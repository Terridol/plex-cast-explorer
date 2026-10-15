"""Plex Cast Explorer: LAN-served, read-only Plex cast directory.

Run with Python 3.10+: python app.py
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import hmac
import secrets
import time
import ipaddress
import subprocess
import re
from functools import lru_cache
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from pathlib import Path
import sqlite3
import threading
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlsplit
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
import xml.etree.ElementTree as ET

ASSET_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
ROOT = Path(os.environ['CAST_EXPLORER_DATA_DIR']).expanduser().resolve() if os.getenv('CAST_EXPLORER_DATA_DIR') else Path(__file__).resolve().parent
ROOT.mkdir(parents=True, exist_ok=True)
ADMIN_AUTH_PATH = ROOT / 'admin_auth.json'
DB_PATH = ROOT / 'cast_explorer.db'
CONFIG_PATH = ROOT / 'config.json'
AUTH_PATH = ROOT / 'auth.json'
ART_CONFIG_PATH = ROOT / 'artwork_config.json'
PORTRAIT_DIR = ROOT / 'portraits'
NETWORK_CONFIG_PATH = ROOT / 'network.json'
HOST = os.getenv('CAST_EXPLORER_HOST', '0.0.0.0')
PORT = int(os.getenv('CAST_EXPLORER_PORT', '8765'))
VERSION = '1.0.0'
SESSION_SECONDS = 14 * 24 * 60 * 60
ADMIN_SESSION_SECONDS = 60 * 60
ARTWORK_MAX_AGE_SECONDS = 180 * 24 * 60 * 60  # Under any six-calendar-month window.
MAX_PROVIDER_JSON_BYTES = 8 * 1024 * 1024  # Bound metadata downloads; large credit pages exceed 1 MiB.
LOGIN_LOCK = threading.Lock()
LOGIN_ATTEMPTS = {}
ALLOWED_REMOTE_IMAGES = {'metadata-static.plex.tv', 'image.tmdb.org', 'assets.plex.tv', 'metadata.provider.plex.tv'}
ART_LOCK = threading.Lock()
ART_CANDIDATES = {}  # Temporary server-side choices; URLs are never accepted from browser clients.
IMAGE_HOSTS = {'image.tmdb.org', 'cdn.theporndb.net', 'api.theporndb.net', 'commons.wikimedia.org', 'upload.wikimedia.org'}
STATE_LOCK = threading.Lock()
STATE = {'running': False, 'phase': 'Not scanned', 'current': 0, 'total': 0, 'errors': 0, 'last_error': '', 'last_finished': None}
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=[
    logging.StreamHandler(),
    RotatingFileHandler(ROOT / 'server.log', maxBytes=2_000_000, backupCount=2, encoding='utf-8'),
])


def load_auth():
    try:
        return json.loads(AUTH_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_auth(new_auth):
    tmp = AUTH_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(new_auth, indent=2), encoding='utf-8')
    os.replace(tmp, AUTH_PATH)
    if os.name != 'nt':
        AUTH_PATH.chmod(0o600)


def set_password(password):
    if len(password) < 12:
        raise ValueError('Choose a password of at least 12 characters.')
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 260_000)
    save_auth({'salt': salt.hex(), 'hash': digest.hex(),
               'session_secret': secrets.token_hex(32)})


def verify_password(password):
    auth = load_auth()
    try:
        salt, expected = bytes.fromhex(auth['salt']), bytes.fromhex(auth['hash'])
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 260_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, KeyError, TypeError):
        return False


def create_session():
    auth = load_auth()
    deadline = int(time.time()) + SESSION_SECONDS
    nonce = secrets.token_hex(12)
    payload = f'{deadline}:{nonce}'
    mac = hmac.new(bytes.fromhex(auth['session_secret']), payload.encode(), hashlib.sha256).hexdigest()
    return payload + ':' + mac


def valid_session(cookie):
    try:
        deadline, nonce, signature = cookie.split(':', 2)
        if not (deadline.isdigit() and int(deadline) >= time.time() and len(nonce) == 24):
            return False
        auth = load_auth()
        expected = hmac.new(bytes.fromhex(auth['session_secret']),
                            f'{deadline}:{nonce}'.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except (KeyError, ValueError, AttributeError):
        return False


def set_admin_password(password):
    if len(password) < 16:
        raise ValueError('Choose a distinct administrator password of at least 16 characters.')
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 360_000)
    payload = {'salt': salt.hex(), 'hash': digest.hex(), 'session_secret': secrets.token_hex(32)}
    tmp = ADMIN_AUTH_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    os.replace(tmp, ADMIN_AUTH_PATH)
    if os.name != 'nt':
        ADMIN_AUTH_PATH.chmod(0o600)


def admin_auth():
    try:
        return json.loads(ADMIN_AUTH_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def verify_admin_password(password):
    data = admin_auth()
    try:
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(data['salt']), 360_000)
        return hmac.compare_digest(actual, bytes.fromhex(data['hash']))
    except (TypeError, KeyError, ValueError):
        return False


def make_admin_session():
    deadline = int(time.time()) + ADMIN_SESSION_SECONDS
    nonce = secrets.token_hex(16)
    payload = f'{deadline}:{nonce}'
    signature = hmac.new(bytes.fromhex(admin_auth()['session_secret']), payload.encode(), hashlib.sha256).hexdigest()
    return f'{payload}:{signature}'


def valid_admin_session(value):
    try:
        deadline, nonce, signature = value.split(':', 2)
        if not deadline.isdigit() or int(deadline) < time.time() or len(nonce) != 32:
            return False
        expected = hmac.new(bytes.fromhex(admin_auth()['session_secret']), f'{deadline}:{nonce}'.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except (ValueError, KeyError, TypeError, AttributeError):
        return False


def approved_admin_address(value):
    """Never infer remote-admin permissions from proxy headers or HTTP Host."""
    configured = os.getenv('CAST_EXPLORER_REMOTE_ADMIN_CIDRS', '').strip()
    if not configured:
        return False
    try:
        addr = ipaddress.ip_address(value)
        return any(addr in ipaddress.ip_network(item.strip(), strict=False)
                   for item in configured.split(',') if item.strip())
    except ValueError:
        return False


def can_try_login(ip):
    now = time.monotonic()
    with LOGIN_LOCK:
        # Simple per-address throttling, with pruning to prevent unbounded memory use.
        for key in list(LOGIN_ATTEMPTS):
            LOGIN_ATTEMPTS[key] = [t for t in LOGIN_ATTEMPTS[key] if t > now - 300]
            if not LOGIN_ATTEMPTS[key]:
                del LOGIN_ATTEMPTS[key]
        return len(LOGIN_ATTEMPTS.get(ip, [])) < 8


def record_failed_login(ip):
    with LOGIN_LOCK:
        LOGIN_ATTEMPTS.setdefault(ip, []).append(time.monotonic())


class SameOriginRedirects(HTTPRedirectHandler):
    """Never forward Plex credentials to a redirected external origin."""
    def __init__(self, base):
        self.base = urlsplit(base)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if (target.scheme, target.netloc) != (self.base.scheme, self.base.netloc):
            raise ValueError('Plex attempted a cross-origin redirect; refusing to forward token')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@contextmanager
def db_open():
    db = sqlite3.connect(DB_PATH, timeout=30)
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA busy_timeout=30000')
        with db:
            yield db
    finally:
        db.close()


def init_db():
    with db_open() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS actors (
            actor_key TEXT PRIMARY KEY, name TEXT NOT NULL, thumb TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS titles (
            rating_key TEXT PRIMARY KEY, section_key TEXT NOT NULL,
            section_name TEXT NOT NULL, media_type TEXT NOT NULL,
            title TEXT NOT NULL, year INTEGER, thumb TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS credits (
            actor_key TEXT NOT NULL REFERENCES actors(actor_key),
            rating_key TEXT NOT NULL REFERENCES titles(rating_key),
            character TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (actor_key, rating_key)
        );
        CREATE INDEX IF NOT EXISTS idx_credits_title ON credits(rating_key);
        CREATE INDEX IF NOT EXISTS idx_titles_section ON titles(section_key);
        CREATE TABLE IF NOT EXISTS actor_art (
            actor_key TEXT PRIMARY KEY, file TEXT NOT NULL, source TEXT NOT NULL,
            source_url TEXT NOT NULL DEFAULT '', attribution TEXT NOT NULL DEFAULT '',
            version INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS enrichment_results (
            actor_key TEXT PRIMARY KEY, status TEXT NOT NULL,
            candidates TEXT NOT NULL DEFAULT '[]', checked_at TEXT NOT NULL DEFAULT '',
            message TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_enrichment_status ON enrichment_results(status);
        ''')


def prune_old_artwork(now=None):
    """Remove stale external metadata, and TMDB portraits after 180 days.

    This is an expiry safeguard, not permission to use a provider or its art.
    Plex images and user-selected non-TMDB portraits are not deleted.
    """
    now = time.time() if now is None else float(now)
    cutoff_ms = int((now - ARTWORK_MAX_AGE_SECONDS) * 1000)
    cutoff_iso = datetime.fromtimestamp(now - ARTWORK_MAX_AGE_SECONDS, timezone.utc).isoformat()
    with db_open() as db:
        expired = db.execute(
            "SELECT file FROM actor_art WHERE source='TMDB' AND version < ?", (cutoff_ms,)
        ).fetchall()
        db.execute("DELETE FROM actor_art WHERE source='TMDB' AND version < ?", (cutoff_ms,))
        # Provider lookup records can include cached TMDB credits and images.
        db.execute("DELETE FROM enrichment_results WHERE checked_at < ?", (cutoff_iso,))
    for row in expired:
        filename = row['file']
        if re.fullmatch(r'[0-9a-f]{64}\.(jpg|png|webp)', filename):
            try:
                (PORTRAIT_DIR / filename).unlink(missing_ok=True)
            except OSError as exc:
                logging.warning('Could not expire an old artwork cache file: %s', exc)
    if expired:
        image_bytes.cache_clear()
    return len(expired)


def load_config():
    try:
        content = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        content = {}
    return {
        'url': os.getenv('PLEX_URL', content.get('url', '')).rstrip('/'),
        'token': os.getenv('PLEX_TOKEN', content.get('token', '')),
    }


def save_config(url: str, token: str | None):
    existing = load_config()
    if token is None:
        token = existing['token']
    data = {'url': url.rstrip('/'), 'token': token}
    tmp = CONFIG_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    os.replace(tmp, CONFIG_PATH)
    # Best-effort POSIX filesystem mode; Windows permissions are inherited.
    if os.name != 'nt':
        CONFIG_PATH.chmod(0o600)
    image_bytes.cache_clear()


def request_plex(path: str, timeout=20) -> bytes:
    config = load_config()
    if not config['url'] or not config['token']:
        raise ValueError('Set your Plex URL and token in Settings first.')
    url = config['url'] + '/' + path.lstrip('/')
    req = Request(url, headers={
        'X-Plex-Token': config['token'],
        'X-Plex-Product': 'Plex Cast Explorer',
        'X-Plex-Client-Identifier': 'plex-cast-explorer-local',
        'Accept': 'application/xml',
    })
    with build_opener(SameOriginRedirects(config['url'])).open(req, timeout=timeout) as response:
        return response.read()


def plex_xml(path: str):
    return ET.fromstring(request_plex(path))


def normal_name(name: str):
    return ' '.join(unicodedata.normalize('NFKC', name).casefold().split())


def state_update(**kwargs):
    with STATE_LOCK:
        STATE.update(kwargs)


def status_snapshot():
    with STATE_LOCK:
        return dict(STATE)


def get_sections():
    xml = plex_xml('/library/sections')
    return [
        {'key': part.get('key', ''), 'name': part.get('title', ''), 'type': part.get('type', '')}
        for part in xml.findall('Directory') if part.get('type') in ('movie', 'show')
    ]


def detail_metadata(rating_key: str):
    # Detail view includes actor identities, portraits and character names; library lists may omit them.
    container = plex_xml('/library/metadata/' + quote(str(rating_key), safe=''))
    return next((item for item in container if item.tag in ('Video', 'Directory')), None)


def upsert_title(db, xml_item, section):
    rating_key = xml_item.get('ratingKey')
    if not rating_key:
        return
    title = xml_item.get('title', 'Untitled')
    year_text = xml_item.get('year', '')
    year = int(year_text) if year_text.isdigit() else None
    db.execute('''INSERT INTO titles (rating_key, section_key, section_name, media_type, title, year, thumb, updated_at)
        VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(rating_key) DO UPDATE SET
        section_key=excluded.section_key, section_name=excluded.section_name,
        media_type=excluded.media_type, title=excluded.title,
        year=excluded.year, thumb=excluded.thumb, updated_at=excluded.updated_at''',
        (rating_key, section['key'], section['name'], section['type'], title, year,
         xml_item.get('thumb', ''), xml_item.get('updatedAt', '')))
    db.execute('DELETE FROM credits WHERE rating_key=?', (rating_key,))
    for role in xml_item.findall('Role'):
        name = (role.get('tag') or '').strip()
        if not name:
            continue
        key = normal_name(name)
        thumb = (role.get('thumb') or '').strip()
        db.execute('''INSERT INTO actors (actor_key,name,thumb) VALUES (?,?,?)
            ON CONFLICT(actor_key) DO UPDATE SET
            thumb=CASE WHEN excluded.thumb!='' THEN excluded.thumb ELSE actors.thumb END''',
            (key, name, thumb))
        db.execute('INSERT OR REPLACE INTO credits (actor_key,rating_key,character) VALUES (?,?,?)',
                   (key, rating_key, role.get('role', '')))


def sync_all(force=False):
    state_update(running=True, phase='Connecting to Plex', current=0, total=0,
                 errors=0, last_error='')
    errors = 0
    try:
        machine_id = plex_xml('/').get('machineIdentifier', '')
        with db_open() as meta_db:
            meta_db.execute('INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)', ('machine_identifier', machine_id))
        sections = get_sections()
        if not sections:
            raise ValueError('No movie or TV libraries found. Check that the token can access this server.')
        with db_open() as db:
            for section in sections:
                state_update(phase='Reading ' + section['name'])
                seen = set()
                all_entries = []
                start = 0
                page_size = 100
                # Use paging rather than requesting an entire very large library at once.
                while True:
                    path = (f"/library/sections/{quote(section['key'], safe='')}/all"
                            f"?type={'1' if section['type'] == 'movie' else '2'}"
                            f"&X-Plex-Container-Start={start}&X-Plex-Container-Size={page_size}")
                    root = plex_xml(path)
                    batch = [node for node in root if node.tag in ('Video', 'Directory') and node.get('ratingKey')]
                    all_entries.extend(batch)
                    seen.update(node.get('ratingKey') for node in batch)
                    start += len(batch)
                    total_size = int(root.get('totalSize') or root.get('size') or len(batch))
                    if not batch or start >= total_size or len(batch) < page_size:
                        break

                existing = {r['rating_key']: r for r in db.execute('''
                    SELECT t.rating_key,t.updated_at,
                        EXISTS (SELECT 1 FROM credits c WHERE c.rating_key=t.rating_key) AS has_credits
                    FROM titles t WHERE t.section_key=?''', (section['key'],))}
                changed = [item for item in all_entries if force or
                           item.get('ratingKey') not in existing or
                           existing[item.get('ratingKey')]['updated_at'] != item.get('updatedAt', '') or
                           not existing[item.get('ratingKey')]['has_credits']]
                state_update(phase=f"Indexing {section['name']}",
                             total=status_snapshot()['total'] + len(changed))

                # Network requests are parallel; SQLite writes remain serial on this thread.
                with ThreadPoolExecutor(max_workers=5) as pool:
                    future_map = {pool.submit(detail_metadata, item.get('ratingKey')): item for item in changed}
                    for future in as_completed(future_map):
                        item = future_map[future]
                        try:
                            detail = future.result()
                            if detail is None:
                                raise ValueError('Metadata item not found')
                            upsert_title(db, detail, section)
                            db.commit()
                        except Exception as exc:
                            errors += 1
                            logging.warning('Cannot index %s: %s', item.get('ratingKey'), exc)
                            state_update(last_error=f"{section['name']}: {str(exc)[:160]}")
                        state_update(current=status_snapshot()['current'] + 1, errors=errors)

                # Only delete titles that are no longer in this completely-listed library.
                for rating_key in set(existing) - seen:
                    db.execute('DELETE FROM credits WHERE rating_key=?', (rating_key,))
                    db.execute('DELETE FROM titles WHERE rating_key=?', (rating_key,))
                db.commit()

            db.execute('DELETE FROM actors WHERE actor_key NOT IN (SELECT actor_key FROM credits)')
            db.commit()
        state_update(phase='Finished' if not errors else 'Finished with warnings')
    except Exception as exc:
        logging.exception('Sync failed')
        state_update(phase='Sync failed', last_error=str(exc), errors=errors + 1)
    finally:
        state_update(running=False, last_finished=datetime.now(timezone.utc).isoformat())


def sync_start(force=False):
    with STATE_LOCK:
        if STATE['running']:
            return False
        STATE['running'] = True
    threading.Thread(target=sync_all, args=(force,), daemon=True).start()
    return True


def get_stats():
    with db_open() as db:
        a = db.execute('SELECT COUNT(*) FROM actors').fetchone()[0]
        t = db.execute('SELECT COUNT(*) FROM titles').fetchone()[0]
        credits = db.execute('SELECT COUNT(*) FROM credits').fetchone()[0]
        machine_row = db.execute("SELECT value FROM metadata WHERE key='machine_identifier'").fetchone()
        sections = [dict(r) for r in db.execute('''SELECT section_key AS key, section_name AS name,
                 media_type AS type,COUNT(*) AS count FROM titles
                 GROUP BY section_key,section_name,media_type ORDER BY section_name COLLATE NOCASE''')]
    return {'actors': a, 'titles': t, 'credits': credits, 'sections': sections, 'machine_id': machine_row['value'] if machine_row else ''}


def list_actors(params):
    search = params.get('search', [''])[0].strip()
    section = params.get('section', [''])[0]
    media_type = params.get('type', [''])[0]
    letter = params.get('letter', [''])[0].upper()
    sort = params.get('sort', ['name'])[0]
    missing_only = params.get('missing', ['0'])[0] == '1'
    try:
        limit = min(120, max(1, int(params.get('limit', ['72'])[0])))
        offset = max(0, int(params.get('offset', ['0'])[0]))
    except ValueError:
        limit, offset = 72, 0
    where = ['1=1']
    args = []
    if search:
        where.append('LOWER(a.name) LIKE ? ESCAPE "\\"')
        args.append('%' + search.casefold().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%')
    if section:
        where.append('t.section_key = ?')
        args.append(section)
    if media_type in ('movie', 'show'):
        where.append('t.media_type = ?')
        args.append(media_type)
    if letter:
        if letter == '#':
            where.append("UPPER(SUBSTR(a.name,1,1)) NOT BETWEEN 'A' AND 'Z'")
        elif len(letter) == 1 and 'A' <= letter <= 'Z':
            where.append('UPPER(SUBSTR(a.name,1,1)) = ?')
            args.append(letter)
    if missing_only:
        where.append("a.thumb='' AND art.actor_key IS NULL")
    clause = ' AND '.join(where)
    with db_open() as db:
        total = db.execute('''SELECT COUNT(*) FROM
            (SELECT a.actor_key FROM actors a JOIN credits c ON c.actor_key=a.actor_key
            JOIN titles t ON c.rating_key=t.rating_key LEFT JOIN actor_art art ON art.actor_key=a.actor_key WHERE '''+clause+''' GROUP BY a.actor_key)''', args).fetchone()[0]
        order = 'appearance_count DESC, a.name COLLATE NOCASE' if sort == 'count' else 'a.name COLLATE NOCASE'
        rows = db.execute('''SELECT a.actor_key AS key,a.name,a.thumb,
            COUNT(DISTINCT t.rating_key) AS appearance_count,
            COUNT(DISTINCT CASE WHEN t.media_type='movie' THEN t.rating_key END) AS movies,
            COUNT(DISTINCT CASE WHEN t.media_type='show' THEN t.rating_key END) AS shows
            FROM actors a JOIN credits c ON c.actor_key=a.actor_key
            JOIN titles t ON c.rating_key=t.rating_key LEFT JOIN actor_art art ON art.actor_key=a.actor_key WHERE '''+clause+
            ' GROUP BY a.actor_key ORDER BY '+order+' LIMIT ? OFFSET ?', args+[limit, offset]).fetchall()
    result = [dict(r) for r in rows]
    with db_open() as db:
        overrides = {row['actor_key']: row['version'] for row in db.execute('SELECT actor_key,version FROM actor_art')}
    for r in result:
        r['image'] = ('/api/image?kind=actor&key=' + quote(r['key']) +
                      ('&v='+str(overrides[r['key']]) if r['key'] in overrides else '')) if (r['thumb'] or r['key'] in overrides) else ''
        r['has_art'] = bool(r['thumb'] or r['key'] in overrides)
        del r['thumb']
    return {'total': total, 'results': result, 'offset': offset, 'limit': limit}


def get_actor(key):
    with db_open() as db:
        actor = db.execute('SELECT actor_key AS key, name, thumb FROM actors WHERE actor_key=?', (key,)).fetchone()
        if not actor:
            return None
        rows = db.execute('''SELECT t.rating_key AS key,t.title,t.year,t.section_name AS library,
            t.media_type AS type,t.thumb,c.character
            FROM titles t JOIN credits c ON t.rating_key=c.rating_key
            WHERE c.actor_key=? ORDER BY t.year DESC,t.title COLLATE NOCASE''', (key,)).fetchall()
    titles = [dict(r) for r in rows]
    for title in titles:
        title['image'] = '/api/image?kind=title&key=' + quote(title['key']) if title['thumb'] else ''
        del title['thumb']
    actor = dict(actor)
    with db_open() as db:
        override = db.execute('SELECT source,source_url,attribution,version FROM actor_art WHERE actor_key=?', (key,)).fetchone()
    actor['image'] = ('/api/image?kind=actor&key=' + quote(key) +
                      ('&v='+str(override['version']) if override else '')) if actor['thumb'] or override else ''
    actor['art'] = dict(override) if override else {'source': 'Plex' if actor['thumb'] else '', 'source_url': '', 'attribution': ''}
    del actor['thumb']
    actor['titles'] = titles
    return actor


@lru_cache(maxsize=512)
def image_bytes(kind, key):
    if kind not in ('actor', 'title'):
        raise ValueError('Unknown image type')
    with db_open() as db:
        if kind == 'actor':
            override = db.execute('SELECT file FROM actor_art WHERE actor_key=?', (key,)).fetchone()
            if override:
                safe_file = override['file']
                if not re.fullmatch(r'[0-9a-f]{64}\.(jpg|png|webp)', safe_file):
                    raise ValueError('Invalid portrait file path')
                return (PORTRAIT_DIR / safe_file).read_bytes()
            row = db.execute('SELECT thumb FROM actors WHERE actor_key=?', (key,)).fetchone()
        else:
            row = db.execute('SELECT thumb FROM titles WHERE rating_key=?', (key,)).fetchone()
    if not row or not row['thumb']:
        raise ValueError('No portrait available')
    thumb = row['thumb']
    if thumb.startswith('/') and not thumb.startswith('//'):
        raw = request_plex(thumb, timeout=12)
    else:
        target = urlsplit(thumb)
        source = urlsplit(load_config()['url'])
        if target.scheme != 'https' or not target.hostname:
            raise ValueError('Unsupported image URL')
        if target.hostname == source.hostname and target.port == source.port:
            raw = request_plex(target.path + ('?' + target.query if target.query else ''), timeout=12)
        elif allowed_https_image_url(thumb, ALLOWED_REMOTE_IMAGES):
            # Restrict both the original URL and *every redirect*. The Plex token
            # is never included in this request or sent to external image hosts.
            req = Request(thumb, headers={'User-Agent': 'PlexCastExplorer/0.4'})
            with build_opener(ArtworkRedirects(ALLOWED_REMOTE_IMAGES)).open(req, timeout=12) as response:
                raw = response.read(4_000_001)
        else:
            raise ValueError('External image source not allowed')
    if len(raw) > 4_000_000:
        raise ValueError('Image too large')
    return raw


# Only classify a browser as on-LAN when the *actual TCP peer* is in an
# established local subnet. Private IPs alone don't prove same-network access.
def windows_lan_networks():
    if os.name != 'nt':
        return []
    command = ('Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | '
               "Where-Object { $_.AddressState -eq 'Preferred' } | "
               'Select-Object IPAddress,PrefixLength | ConvertTo-Json -Compress')
    try:
        kwargs = {'capture_output': True, 'text': True, 'timeout': 8}
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        proc = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                               '-Command', command], **kwargs)
        if proc.returncode:
            logging.warning('Windows network discovery: %s', proc.stderr[-500:])
            return []
        items = json.loads(proc.stdout.strip() or '[]')
        if isinstance(items, dict):
            items = [items]
        nets = []
        for item in items:
            try:
                address = ipaddress.ip_address(item['IPAddress'])
                prefix = int(item['PrefixLength'])
                if (address.version != 4 or address.is_loopback or
                    address.is_link_local or not 8 <= prefix <= 32):
                    continue
                nets.append(ipaddress.ip_network(f'{address}/{prefix}', strict=False))
            except (ValueError, KeyError, TypeError):
                continue
        return nets
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        logging.warning('Cannot discover Windows subnets: %s', exc)
        return []


@lru_cache(maxsize=1)
def lan_networks():
    discovered = windows_lan_networks()
    configured = os.getenv('CAST_EXPLORER_LAN_CIDRS', '')
    try:
        settings = json.loads(NETWORK_CONFIG_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        settings = {}
    configured += ',' + ','.join(settings.get('additional_lan_cidrs', []))
    for value in configured.split(','):
        if value.strip():
            try:
                discovered.append(ipaddress.ip_network(value.strip(), strict=False))
            except ValueError:
                logging.warning('Ignoring invalid LAN CIDR %s', value)
    return tuple(set(discovered))


def peer_on_lan(peer):
    try:
        addr = ipaddress.ip_address(peer)
        if addr.is_loopback:
            return True
        return any(addr in net for net in lan_networks())
    except ValueError:
        return False


def plex_link_config(peer, server_ip):
    """Return public/non-secret browser link base. Never include Plex tokens."""
    if not peer_on_lan(peer):
        return {'mode': 'remote', 'base': 'https://app.plex.tv/desktop/'}
    try:
        netconf = json.loads(NETWORK_CONFIG_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        netconf = {}
    manual = os.getenv('CAST_EXPLORER_PLEX_LAN_URL', '').strip() or netconf.get('plex_lan_url', '')
    if manual:
        parsed = urlsplit(manual)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
            logging.warning('Invalid Plex LAN URL override, falling back to detected host')
            manual = ''
    if manual:
        base = manual.rstrip('/')
    else:
        # The connected socket's local IP is the interface the browser actually reached.
        # When visiting from localhost, loopback is correct too.
        host = f'[{server_ip}]' if ':' in server_ip else server_ip
        port = urlsplit(load_config()['url']).port or 32400
        base = f'http://{host}:{port}'
    return {'mode': 'local', 'base': base + '/web/index.html'}


def provider_enabled(name):
    """Opt-in to third-party providers requiring additional terms compliance.

    TMDB and Wikimedia are OFF by default. Saved tokens do not activate TMDB.
    The operator is responsible for provider-specific permitted uses.
    """
    flag = {'tmdb': 'CAST_EXPLORER_ENABLE_TMDB',
            'wikimedia': 'CAST_EXPLORER_ENABLE_WIKIMEDIA'}.get(name)
    return bool(flag and os.environ.get(flag, '').strip() == '1')


def artwork_keys():
    try:
        obj = json.loads(ART_CONFIG_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        obj = {}
    return {'tmdb': os.getenv('CAST_EXPLORER_TMDB_TOKEN', obj.get('tmdb', '')),
            'theporndb': os.getenv('CAST_EXPLORER_TPDB_TOKEN', obj.get('theporndb', ''))}


def save_artwork_keys(tmdb, tpdb):
    keys = artwork_keys()
    if tmdb:
        keys['tmdb'] = tmdb
    if tpdb:
        keys['theporndb'] = tpdb
    tmp = ART_CONFIG_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(keys, indent=2), encoding='utf-8')
    os.replace(tmp, ART_CONFIG_PATH)
    if os.name != 'nt':
        ART_CONFIG_PATH.chmod(0o600)


def allowed_https_image_url(url, allowed_hosts):
    """Only permit HTTPS artwork URLs on trusted hosts and standard TLS ports."""
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == 'https' and parsed.hostname in allowed_hosts
                and parsed.username is None and parsed.password is None
                and parsed.port in (None, 443))
    except ValueError:  # E.g. malformed port, invalid URL brackets.
        return False


class ArtworkRedirects(HTTPRedirectHandler):
    """Apply the approved image host/port checks to *every* HTTP redirect."""
    def __init__(self, allowed_hosts=None):
        self.allowed_hosts = IMAGE_HOSTS if allowed_hosts is None else allowed_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_https_image_url(newurl, self.allowed_hosts):
            raise ValueError('Untrusted image redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def external_image(url):
    if not allowed_https_image_url(url, IMAGE_HOSTS):
        raise ValueError('Image host not permitted')
    request = Request(url, headers={'User-Agent': 'PlexCastExplorer/0.4 (home library artwork browser)',
                                    'Accept': 'image/jpeg,image/png,image/webp'})
    with build_opener(ArtworkRedirects()).open(request, timeout=12) as response:
        mime = response.headers.get_content_type()
        if mime not in ('image/jpeg', 'image/png', 'image/webp'):
            raise ValueError('Not a supported image format')
        data = response.read(4_000_001)
    if len(data) > 4_000_000 or not data:
        raise ValueError('Image is empty or too large')
    if data.startswith(b'\xff\xd8\xff'):
        return data, 'jpg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return data, 'png'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return data, 'webp'
    raise ValueError('File is not a supported image')


def provider_json(url, bearer=None):
    host = urlsplit(url).hostname
    if urlsplit(url).scheme != 'https' or host not in {'api.themoviedb.org','api.theporndb.net','www.wikidata.org'}:
        raise ValueError('Unknown metadata provider')
    headers = {'Accept': 'application/json', 'User-Agent': 'PlexCastExplorer/0.4 (personal library artwork browser)'}
    if bearer:
        headers['Authorization'] = 'Bearer ' + bearer
    req = Request(url, headers=headers)
    # Metadata host may not redirect, to avoid forwarding a bearer token.
    with build_opener(SameOriginRedirects(f'https://{host}')).open(req, timeout=13) as res:
        # A 1 MiB read truncated valid ThePornDB performer-scene pages and
        # produced misleading JSONDecodeError: Unterminated string. Read at
        # most one byte past the bounded limit to distinguish an oversized
        # complete response from malformed JSON. Never parse truncated bytes.
        payload = res.read(MAX_PROVIDER_JSON_BYTES + 1)
    if len(payload) > MAX_PROVIDER_JSON_BYTES:
        raise ValueError('Metadata provider response exceeds the 8 MiB safety limit')
    if not payload:
        raise ValueError('Metadata provider returned an empty response')
    return json.loads(payload)


def new_art_candidate(actor_key, name, url, source, reference, credit):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in IMAGE_HOSTS:
        return None
    token = secrets.token_urlsafe(24)
    record = {'actor_key': actor_key, 'name': name, 'url': url, 'source': source,
              'reference': reference, 'credit': credit, 'expires': time.time() + 900}
    with ART_LOCK:
        for old in list(ART_CANDIDATES):
            if ART_CANDIDATES[old]['expires'] < time.time():
                del ART_CANDIDATES[old]
        if len(ART_CANDIDATES) >= 300:
            ART_CANDIDATES.pop(next(iter(ART_CANDIDATES)))
        ART_CANDIDATES[token] = record
    return {'id': token, 'name': name, 'source': source, 'reference': reference,
            'preview': '/api/art/preview?id=' + quote(token)}


def candidate(token):
    with ART_LOCK:
        obj = ART_CANDIDATES.get(token)
        if not obj or obj['expires'] < time.time():
            raise ValueError('Artwork choice expired; search again')
        return dict(obj)


def find_art(key):
    with db_open() as db:
        actor = db.execute('SELECT name FROM actors WHERE actor_key=?', (key,)).fetchone()
    if not actor:
        raise ValueError('Performer not found')
    name = actor['name']
    keys = artwork_keys()
    results = []
    warnings = []
    def add(name_found, image, source, reference, credit):
        if normal_name(name_found) != normal_name(name):
            return
        choice = new_art_candidate(key, name_found, image, source, reference, credit)
        if choice:
            results.append(choice)
    if keys['tmdb'] and provider_enabled('tmdb'):
        try:
            response = provider_json('https://api.themoviedb.org/3/search/person?' + urlencode({'query': name, 'include_adult': 'true'}), keys['tmdb'])
            for item in response.get('results', [])[:12]:
                path = item.get('profile_path') or ''
                if re.fullmatch(r'/[a-zA-Z0-9_./-]+\.(jpg|png|webp)', path, re.I):
                    add(item.get('name', ''), 'https://image.tmdb.org/t/p/w185' + path,
                        'TMDB', f'https://www.themoviedb.org/person/{item["id"]}', 'The Movie Database (TMDB)')
        except Exception as exc:
            logging.warning('TMDB portrait search failed: %s', exc)
            warnings.append('TMDB lookup unavailable: ' + str(exc)[:140])
    if keys['theporndb']:
        try:
            response = provider_json('https://api.theporndb.net/performers?' + urlencode({'q': name}), keys['theporndb'])
            for item in response.get('data', [])[:12]:
                portrait = item.get('image') or ''
                if isinstance(portrait, dict):
                    portrait = portrait.get('url') or portrait.get('full') or portrait.get('medium') or ''
                if isinstance(portrait, str):
                    add(item.get('name', ''), portrait, 'ThePornDB',
                        f'https://theporndb.net/performers/{item["id"]}' if item.get('id') else 'https://theporndb.net/',
                        'ThePornDB')
        except Exception as exc:
            logging.warning('ThePornDB portrait search failed: %s', exc)
            warnings.append('ThePornDB lookup unavailable: ' + str(exc)[:140])
    if provider_enabled('wikimedia'):
        try:
            response = provider_json('https://www.wikidata.org/w/api.php?' + urlencode({
                'action': 'wbsearchentities', 'search': name, 'language': 'en', 'format': 'json', 'limit': 6}))
            hits = [x for x in response.get('search', []) if normal_name(x.get('label', '')) == normal_name(name)][:3]
            if hits:
                more = provider_json('https://www.wikidata.org/w/api.php?' + urlencode({
                    'action': 'wbgetentities', 'ids': '|'.join(x['id'] for x in hits), 'props': 'claims', 'format': 'json'}))
                for hit in hits:
                    claims = more.get('entities', {}).get(hit['id'], {}).get('claims', {}).get('P18', [])
                    for claim in claims[:1]:
                        try:
                            filename = claim['mainsnak']['datavalue']['value']
                            if not isinstance(filename, str) or not filename.lower().endswith(('.jpg','.jpeg','.png','.webp')):
                                continue
                            file_id = filename.replace(' ', '_')
                            image = 'https://commons.wikimedia.org/wiki/Special:Redirect/file/' + quote(file_id, safe='') + '?width=300'
                            reference = 'https://commons.wikimedia.org/wiki/File:' + quote(file_id, safe='')
                            add(hit['label'], image, 'Wikimedia Commons', reference, 'Wikimedia Commons — review image license and attribution')
                        except (KeyError, TypeError):
                            continue
        except Exception as exc:
            logging.warning('Wikimedia portrait search failed: %s', exc)
            warnings.append('Wikimedia lookup unavailable: ' + str(exc)[:140])
    return {'actor': name, 'results': results[:25], 'warnings': warnings,
            'configured': {'tmdb': bool(keys['tmdb']) and provider_enabled('tmdb'), 'theporndb': bool(keys['theporndb']), 'wikimedia': provider_enabled('wikimedia')}}


def apply_art(actor_key, choice_token):
    entry = candidate(choice_token)
    if entry['actor_key'] != actor_key:
        raise ValueError('Artwork choice does not belong to this performer')
    with db_open() as db:
        if not db.execute('SELECT 1 FROM actors WHERE actor_key=?', (actor_key,)).fetchone():
            raise ValueError('Performer not found')
    content, ext = verified_portrait_image(entry['url'])
    PORTRAIT_DIR.mkdir(exist_ok=True)
    name = hashlib.sha256(actor_key.encode('utf-8')).hexdigest() + '.' + ext
    temp = PORTRAIT_DIR / (name + '.tmp')
    temp.write_bytes(content)
    os.replace(temp, PORTRAIT_DIR / name)
    with db_open() as db:
        db.execute('INSERT INTO actor_art(actor_key,file,source,source_url,attribution,version) VALUES (?,?,?,?,?,?) '
                   'ON CONFLICT(actor_key) DO UPDATE SET file=excluded.file,source=excluded.source, '
                   'source_url=excluded.source_url,attribution=excluded.attribution,version=excluded.version',
                   (actor_key, name, entry['source'], entry['reference'], entry['credit'], int(time.time()*1000)))
    image_bytes.cache_clear()


def remove_art(actor_key):
    with db_open() as db:
        db.execute('DELETE FROM actor_art WHERE actor_key=?', (actor_key,))
    image_bytes.cache_clear()


# Background artwork enrichment. Only verified, multi-credit matches are applied without review.
ENRICH_LOCK = threading.Lock()
ENRICH_STOP = threading.Event()
ENRICH_STATE = {'running': False, 'phase': 'Idle', 'checked': 0, 'total': 0,
                'applied': 0, 'review': 0, 'unmatched': 0, 'errors': 0, 'last_error': ''}
ENRICH_REQUEST_LOCK = threading.Lock()
ENRICH_LAST_REQUEST = 0.0
REVIEW_BATCH_LOCK = threading.Lock()
REVIEW_MUTATION_LOCK = threading.RLock()
REVIEW_BATCH_STATE = {'running': False, 'checked': 0, 'total': 0, 'applied': 0, 'skipped': 0, 'failed': 0, 'last_error': ''}


def normalize_title(value):
    # No fuzzy substrings: titles like "Crash" and "Crash Course" must not match.
    value = unicodedata.normalize('NFKD', str(value or '')).casefold()
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[a-z0-9]+', value))


def credit_year(row):
    val = row.get('year')
    if val not in (None, ''):
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    date = str(row.get('release_date') or row.get('first_air_date') or row.get('date') or '')
    return int(date[:4]) if re.match(r'^\d{4}', date) else None


def credit_matches(local_titles, remote_credits, source):
    """Require real title equality and compatible dates; never infer identity from a name alone."""
    matched = {}
    for local in local_titles:
        target = normalize_title(local['title'])
        if not target or len(target) < 3:
            continue
        year_a = credit_year(local)
        for remote in remote_credits:
            if source == 'TMDB':
                rt = remote.get('media_type', '')
                if rt and rt not in ('movie' if local['media_type'] == 'movie' else 'tv',):
                    continue
            else:
                # TPDB's scene endpoint contains scenes, not TV show filmographies.
                if local['media_type'] != 'movie':
                    continue
            names = (remote.get('title'), remote.get('original_title'),
                     remote.get('name'), remote.get('original_name'))
            if target not in {normalize_title(n) for n in names if n}:
                continue
            year_b = credit_year(remote)
            if year_a is not None and year_b is not None and abs(year_a - year_b) > 1:
                continue
            exact_year = year_a is not None and year_b is not None and year_a == year_b
            # One year tolerance for alternate release dates but it is not year verification.
            key = (local['title'].casefold(), year_a, local['media_type'])
            p_role = str(local.get('character') or '').strip()
            e_role = str(remote.get('character') or '').strip()
            conflict = bool(p_role and e_role and normalize_title(p_role) != normalize_title(e_role))
            matched[key] = {'title': local['title'], 'year': year_a,
                            'external_year': year_b, 'year_verified': exact_year,
                            'plex_character': p_role, 'provider_character': e_role,
                            'role_conflict': conflict}
            break
    return list(matched.values())


def is_strong_match(item):
    matches = item.get('matches', [])
    return (len(matches) >= 2 and sum(bool(m['year_verified']) for m in matches) >= 1
            and not any(m.get('role_conflict') for m in matches))


def actor_titles_for_matching(key):
    with db_open() as db:
        a = db.execute('SELECT name FROM actors WHERE actor_key=?', (key,)).fetchone()
        if a is None:
            return None, []
        titles = [dict(r) for r in db.execute('''
            SELECT t.title,t.year,t.media_type,c.character FROM titles t
            JOIN credits c ON c.rating_key=t.rating_key WHERE c.actor_key=?
            ORDER BY t.year DESC,t.title COLLATE NOCASE''', (key,))]
    return a['name'], titles


def paced_provider_json(url, bearer):
    # One worker, conservative API pacing. Browser manual lookups remain independent.
    global ENRICH_LAST_REQUEST
    with ENRICH_REQUEST_LOCK:
        wait = 0.8 - (time.monotonic() - ENRICH_LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        ENRICH_LAST_REQUEST = time.monotonic()
        return provider_json(url, bearer)


def provider_other_credits(local, remote_credits, count=10):
    """Non-overlapping provider titles give reviewers useful identity context."""
    local_names = {normalize_title(t['title']) for t in local}
    seen = set()
    out = []
    for item in remote_credits:
        title = item.get('title') or item.get('name') or ''
        normalized = normalize_title(title)
        if len(normalized) < 3 or normalized in local_names or normalized in seen:
            continue
        seen.add(normalized)
        out.append({'title': str(title)[:180], 'year': credit_year(item)})
        if len(out) >= count:
            break
    return out


def portrait_from_tpdb(item):
    image = item.get('image') or ''
    if isinstance(image, dict):
        image = image.get('url') or image.get('full') or image.get('medium') or ''
    return image if isinstance(image, str) else ''


def verified_portrait_candidates(actor_key):
    name, local = actor_titles_for_matching(actor_key)
    if not name:
        return [], ['Actor no longer exists']
    keys = artwork_keys()
    found, errors = [], []
    if keys['tmdb'] and provider_enabled('tmdb'):
        try:
            search = paced_provider_json('https://api.themoviedb.org/3/search/person?' + urlencode({
                'query': name, 'include_adult': 'true'}), keys['tmdb'])
            matching = [p for p in search.get('results', [])
                        if normal_name(p.get('name', '')) == normal_name(name)
                        and isinstance(p.get('id'), int) and
                        re.fullmatch(r'/[a-zA-Z0-9_./-]+\.(?:jpg|png|webp)', p.get('profile_path') or '', re.I)]
            for item in matching[:4]:
                try:
                    credits = paced_provider_json(f'https://api.themoviedb.org/3/person/{item["id"]}/combined_credits', keys['tmdb'])
                    matches = credit_matches(local, credits.get('cast', []), 'TMDB')
                    if matches:
                        found.append({'name': item['name'], 'source': 'TMDB',
                                      'url': 'https://image.tmdb.org/t/p/w342' + item['profile_path'],
                                      'reference': f'https://www.themoviedb.org/person/{item["id"]}',
                                      'credit': 'The Movie Database (TMDB)', 'matches': matches,
                                      'other_titles': provider_other_credits(local, credits.get('cast', []))})
                except Exception as exc:
                    errors.append('TMDB credits: ' + str(exc)[:100])
        except Exception as exc:
            errors.append('TMDB search: ' + str(exc)[:100])
    if keys['theporndb']:
        try:
            response = paced_provider_json('https://api.theporndb.net/performers?' + urlencode({'q': name}), keys['theporndb'])
            for item in (response.get('data') or [])[:10]:
                if normal_name(item.get('name', '')) != normal_name(name):
                    continue
                ident = item.get('_id') or item.get('id')
                image = portrait_from_tpdb(item)
                if not ident or not image:
                    continue
                if not (urlsplit(image).scheme == 'https' and urlsplit(image).hostname in IMAGE_HOSTS):
                    continue
                try:
                    url = 'https://api.theporndb.net/performers/' + quote(str(ident), safe='') + '/scenes?' + urlencode({'page': 1, 'per_page': 100})
                    response_scenes = paced_provider_json(url, keys['theporndb'])
                    scene_data = response_scenes.get('data', [])
                    if not isinstance(scene_data, list):
                        scene_data = []
                    matches = credit_matches(local, scene_data, 'ThePornDB')
                    if matches:
                        found.append({'name': item['name'], 'source': 'ThePornDB',
                                      'url': image,
                                      'reference': 'https://theporndb.net/performers/' + quote(str(ident), safe=''),
                                      'credit': 'ThePornDB', 'matches': matches,
                                      'other_titles': provider_other_credits(local, scene_data)})
                except Exception as exc:
                    errors.append('ThePornDB credits: ' + str(exc)[:100])
        except Exception as exc:
            errors.append('ThePornDB search: ' + str(exc)[:100])
    # Best verified credit overlap first. Name-only matches never enter auto approval.
    found.sort(key=lambda c: (len(c['matches']), sum(bool(m['year_verified']) for m in c['matches'])), reverse=True)
    return found[:8], errors


def singleton_is_verified(actor_name, candidates, warning=''):
    """A unique candidate with *an actual Plex credit overlap*, not just one name result.

    An external provider can return one incorrect namesake. Require matching
    performer names, a shared title, compatible dates, no conflicting credited
    roles, an allowed image host, and no incomplete provider lookups.
    """
    if warning or len(candidates) != 1:
        return False
    entry = candidates[0]
    if not isinstance(entry, dict) or not actor_name or not entry.get('name'):
        return False
    if normal_name(actor_name) != normal_name(entry['name']):
        return False
    if entry.get('source') not in ('TMDB', 'ThePornDB'):
        return False
    u = urlsplit(str(entry.get('url', '')))
    if u.scheme != 'https' or u.hostname not in IMAGE_HOSTS:
        return False
    matches = entry.get('matches')
    if not isinstance(matches, list) or not matches:
        return False
    for m in matches:
        if not isinstance(m, dict) or not normalize_title(m.get('title')) or m.get('role_conflict'):
            return False
        ya, yb = credit_year({'year': m.get('year')}), credit_year({'year': m.get('external_year')})
        if ya is not None and yb is not None and abs(ya-yb) > 1:
            return False
    return True


def choose_automatic_candidate(candidates, actor_name=None, errors=None):
    if not candidates or errors:
        return None
    if len(candidates) == 1:
        one = candidates[0]
        # Exact-name and matching-title verification is required even for
        # singletons; a sole search result is NOT itself identity evidence.
        if singleton_is_verified(actor_name or one.get('name', ''), candidates):
            return one
        return None
    if not is_strong_match(candidates[0]):
        return None
    best = candidates[0]
    primary = (len(best['matches']), sum(bool(m['year_verified']) for m in best['matches']))
    runner = candidates[1]
    secondary = (len(runner['matches']), sum(bool(m['year_verified']) for m in runner['matches']))
    return best if primary != secondary else None


def verified_portrait_image(url):
    """Prefer a higher-resolution TMDB profile and fall back to legacy size."""
    if url.startswith('https://image.tmdb.org/t/p/w342/'):
        try:
            return external_image(url.replace('/t/p/w342/', '/t/p/h632/', 1))
        except Exception:
            pass
    return external_image(url)


def save_verified_art(actor_key, entry):
    with db_open() as db:
        if not db.execute('SELECT 1 FROM actors WHERE actor_key=?', (actor_key,)).fetchone():
            raise ValueError('Actor no longer exists')
    content, ext = verified_portrait_image(entry['url'])
    PORTRAIT_DIR.mkdir(exist_ok=True)
    name = hashlib.sha256(actor_key.encode('utf-8')).hexdigest() + '.' + ext
    temp = PORTRAIT_DIR / (name + '.tmp')
    temp.write_bytes(content)
    os.replace(temp, PORTRAIT_DIR / name)
    with db_open() as db:
        db.execute('''INSERT INTO actor_art(actor_key,file,source,source_url,attribution,version)
        VALUES (?,?,?,?,?,?) ON CONFLICT(actor_key) DO UPDATE SET
        file=excluded.file,source=excluded.source,source_url=excluded.source_url,
        attribution=excluded.attribution,version=excluded.version''',
            (actor_key, name, entry['source'], entry['reference'],
             entry.get('credit', '') + (' — credits corroborated' if entry.get('matches') else ''),
             int(time.time()*1000)))
    image_bytes.cache_clear()


def enrichment_status():
    with ENRICH_LOCK:
        data = dict(ENRICH_STATE)
    with REVIEW_BATCH_LOCK:
        data['single_batch'] = dict(REVIEW_BATCH_STATE)
    with db_open() as db:
        for row in db.execute('SELECT status,COUNT(*) AS n FROM enrichment_results GROUP BY status'):
            data['db_' + row['status']] = row['n']
        data['review_waiting'] = db.execute("SELECT COUNT(*) FROM enrichment_results WHERE status='review'").fetchone()[0]
        data['remaining'] = db.execute('''SELECT COUNT(*) FROM actors a
            WHERE a.thumb='' AND NOT EXISTS(SELECT 1 FROM actor_art art WHERE art.actor_key=a.actor_key)
            AND NOT EXISTS(SELECT 1 FROM enrichment_results r WHERE r.actor_key=a.actor_key)''').fetchone()[0]
    return data


def pending_enrichment_keys():
    with db_open() as db:
        return [r[0] for r in db.execute('''SELECT a.actor_key FROM actors a JOIN credits c ON c.actor_key=a.actor_key
            WHERE a.thumb='' AND NOT EXISTS(SELECT 1 FROM actor_art art WHERE art.actor_key=a.actor_key)
            AND NOT EXISTS(SELECT 1 FROM enrichment_results r WHERE r.actor_key=a.actor_key)
            GROUP BY a.actor_key ORDER BY COUNT(c.rating_key) DESC,a.actor_key''')]


def remember_enrichment(actor_key, status, candidates=None, message=''):
    with db_open() as db:
        db.execute('''INSERT INTO enrichment_results(actor_key,status,candidates,checked_at,message)
            VALUES (?,?,?,?,?) ON CONFLICT(actor_key) DO UPDATE SET status=excluded.status,
            candidates=excluded.candidates,checked_at=excluded.checked_at,message=excluded.message''',
            (actor_key, status, json.dumps(candidates or [], ensure_ascii=False),
             datetime.now(timezone.utc).isoformat(), message[:500]))


def enrichment_worker():
    try:
        keys = pending_enrichment_keys()
        with ENRICH_LOCK:
            ENRICH_STATE.update(phase='Finding artwork', checked=0, total=len(keys),
                                applied=0, review=0, unmatched=0, errors=0, last_error='')
        consecutive_provider_failures = 0
        for key in keys:
            if ENRICH_STOP.is_set():
                break
            try:
                choices, errors = verified_portrait_candidates(key)
                # Avoid burning through a large library on bad credentials, outages,
                # or rate limits. The administrator can fix the provider and retry.
                if errors and not choices:
                    consecutive_provider_failures += 1
                else:
                    consecutive_provider_failures = 0
                actor_name, _ = actor_titles_for_matching(key)
                automatic = choose_automatic_candidate(choices, actor_name=actor_name, errors=errors)
                if automatic:
                    try:
                        save_verified_art(key, automatic)
                        status, saved = 'auto', []
                    except Exception as exc:
                        errors.append('Portrait download: ' + str(exc)[:100])
                        status, saved = 'review', choices
                elif choices:
                    status, saved = 'review', choices
                else:
                    status, saved = ('error' if errors else 'unmatched'), []
                remember_enrichment(key, status, saved, '; '.join(errors))
                with ENRICH_LOCK:
                    if status == 'auto': ENRICH_STATE['applied'] += 1
                    elif status == 'review': ENRICH_STATE['review'] += 1
                    elif status == 'unmatched': ENRICH_STATE['unmatched'] += 1
                    else: ENRICH_STATE['errors'] += 1
                    if errors: ENRICH_STATE['last_error'] = '; '.join(errors)[:220]
            except Exception as exc:
                logging.warning('Bulk enrichment for %s failed: %s', key, exc)
                remember_enrichment(key, 'error', [], str(exc))
                with ENRICH_LOCK:
                    ENRICH_STATE['errors'] += 1
                    ENRICH_STATE['last_error'] = str(exc)[:220]
            with ENRICH_LOCK:
                ENRICH_STATE['checked'] += 1
            if consecutive_provider_failures >= 3:
                with ENRICH_LOCK:
                    ENRICH_STATE['last_error'] = 'Scan paused after three provider lookup failures. Verify your provider credentials and availability; then retry errors.'
                ENRICH_STOP.set()
                break
    finally:
        with ENRICH_LOCK:
            ENRICH_STATE['running'] = False
            ENRICH_STATE['phase'] = 'Paused' if ENRICH_STOP.is_set() else 'Finished'


def enrichment_start():
    with ENRICH_LOCK:
        if ENRICH_STATE['running']:
            return False
        if not any(artwork_keys().values()):
            raise ValueError('Configure TMDB or ThePornDB first')
        ENRICH_STOP.clear()
        ENRICH_STATE['running'] = True
        ENRICH_STATE['phase'] = 'Preparing'
    threading.Thread(target=enrichment_worker, daemon=True, name='PortraitEnrichment').start()
    return True


def enrichment_stop():
    ENRICH_STOP.set()



def retry_enrichment_errors():
    with ENRICH_LOCK:
        if ENRICH_STATE['running']:
            raise ValueError('Pause the running scan before retrying errors')
    with db_open() as db:
        count = db.execute("DELETE FROM enrichment_results WHERE status='error'").rowcount
    return count


def review_single_batch_worker():
    """Apply previously queued, unambiguous one-result portraits in background.

    Items with historical provider errors, mismatched names/roles, or incomplete
    evidence stay in the queue. No Plex metadata is modified.
    """
    try:
        with db_open() as db:
            rows = db.execute("""SELECT e.actor_key, a.name FROM enrichment_results e
                JOIN actors a ON a.actor_key=e.actor_key WHERE e.status='review'
                ORDER BY e.checked_at ASC""").fetchall()
        with REVIEW_BATCH_LOCK:
            REVIEW_BATCH_STATE.update(total=len(rows), checked=0, applied=0,
                                      skipped=0, failed=0, last_error='')
        for row in rows:
            try:
                with REVIEW_MUTATION_LOCK:
                    with db_open() as db:
                        current = db.execute("SELECT candidates, message FROM enrichment_results WHERE actor_key=? AND status='review'",
                                             (row['actor_key'],)).fetchone()
                    if not current:
                        with REVIEW_BATCH_LOCK: REVIEW_BATCH_STATE['skipped'] += 1
                        continue
                    try:
                        choices = json.loads(current['candidates'])
                    except (ValueError, TypeError):
                        choices = []
                    if not singleton_is_verified(row['name'], choices, current['message']):
                        with REVIEW_BATCH_LOCK: REVIEW_BATCH_STATE['skipped'] += 1
                        continue
                    save_verified_art(row['actor_key'], choices[0])
                    remember_enrichment(row['actor_key'], 'auto', [], 'Unique credit-matched candidate auto-accepted')
                    with REVIEW_BATCH_LOCK: REVIEW_BATCH_STATE['applied'] += 1
            except Exception as exc:
                logging.warning('Single-result portrait apply failed for %s: %s', row['actor_key'], exc)
                with REVIEW_BATCH_LOCK:
                    REVIEW_BATCH_STATE['failed'] += 1
                    REVIEW_BATCH_STATE['last_error'] = str(exc)[:220]
            finally:
                with REVIEW_BATCH_LOCK: REVIEW_BATCH_STATE['checked'] += 1
    finally:
        with REVIEW_BATCH_LOCK: REVIEW_BATCH_STATE['running'] = False


def review_single_batch_start():
    with REVIEW_BATCH_LOCK:
        if REVIEW_BATCH_STATE['running']:
            return False
        REVIEW_BATCH_STATE['running'] = True
    threading.Thread(target=review_single_batch_worker, daemon=True,
                     name='SinglePortraitReviewBatch').start()
    return True


def review_enrichment(limit=12):
    """Give the administrator independently inspectable Plex credit context.

    Only the server-local administrator may call this endpoint. Candidate URLs
    remain behind the existing image proxy, never sent to the browser as images.
    """
    with db_open() as db:
        rows = db.execute("SELECT e.actor_key,a.name,e.candidates,e.message FROM enrichment_results e "
                          "JOIN actors a ON e.actor_key=a.actor_key WHERE e.status='review' "
                          'ORDER BY e.checked_at DESC LIMIT ?', (min(max(int(limit), 1), 30),)).fetchall()
        result = []
        for row in rows:
            try:
                opts = json.loads(row['candidates'])
            except (ValueError, TypeError):
                opts = []
            if not isinstance(opts, list):
                opts = []
            for i, opt in enumerate(opts):
                opt['preview'] = '/api/enrich/preview?key=' + quote(row['actor_key']) + '&i=' + str(i)
            credit_count = db.execute('SELECT COUNT(*) FROM credits WHERE actor_key=?', (row['actor_key'],)).fetchone()[0]
            plex_titles = [dict(r) for r in db.execute("""
                SELECT t.title,t.year,t.media_type,t.section_name AS library,
                    c.character,t.rating_key AS key FROM titles t
                JOIN credits c ON c.rating_key=t.rating_key
                WHERE c.actor_key=? ORDER BY t.year DESC,t.title COLLATE NOCASE LIMIT 30
            """, (row['actor_key'],))]
            result.append({'key': row['actor_key'], 'name': row['name'],
                           'choices': opts, 'warning': row['message'],
                           'quick_eligible': singleton_is_verified(row['name'], opts, row['message']),
                           'plex_titles': plex_titles, 'plex_title_count': credit_count})
    return result


def _reject_enrichment_candidate(actor_key, idx):
    """Reject only this identity candidate; retain remaining alternatives for review."""
    with db_open() as db:
        row = db.execute('SELECT candidates FROM enrichment_results WHERE actor_key=? AND status=?',
                         (actor_key, 'review')).fetchone()
        if not row:
            raise ValueError('No review is pending for this performer')
        options = json.loads(row['candidates'])
        if type(idx) is not int or not 0 <= idx < len(options):
            raise ValueError('Unknown artwork selection')
        options.pop(idx)
        if options:
            db.execute('UPDATE enrichment_results SET candidates=?,message=? WHERE actor_key=?',
                       (json.dumps(options, ensure_ascii=False), 'Candidate rejected by administrator', actor_key))
        else:
            db.execute("UPDATE enrichment_results SET status='skipped',candidates='[]',message=? WHERE actor_key=?",
                       ('All proposed portraits rejected; no portrait was applied', actor_key))
    return bool(options)


def _approve_enrichment(actor_key, idx):
    with db_open() as db:
        row = db.execute('SELECT candidates FROM enrichment_results WHERE actor_key=? AND status=?',
                         (actor_key, 'review')).fetchone()
    if not row:
        raise ValueError('No review is pending for this performer')
    options = json.loads(row['candidates'])
    if not isinstance(idx, int) or not 0 <= idx < len(options):
        raise ValueError('Unknown artwork selection')
    save_verified_art(actor_key, options[idx])
    remember_enrichment(actor_key, 'approved', [], 'Reviewed and approved')


def _skip_enrichment(actor_key):
    with db_open() as db:
        row = db.execute('SELECT 1 FROM enrichment_results WHERE actor_key=? AND status=?', (actor_key, 'review')).fetchone()
    if not row:
        raise ValueError('No review is pending for this performer')
    remember_enrichment(actor_key, 'skipped', [], 'Skipped by administrator')


def reject_enrichment_candidate(actor_key, idx):
    with REVIEW_MUTATION_LOCK:
        return _reject_enrichment_candidate(actor_key, idx)


def approve_enrichment(actor_key, idx):
    with REVIEW_MUTATION_LOCK:
        return _approve_enrichment(actor_key, idx)


def skip_enrichment(actor_key):
    with REVIEW_MUTATION_LOCK:
        return _skip_enrichment(actor_key)


def get_enrichment_preview(actor_key, idx):
    with db_open() as db:
        row = db.execute('SELECT candidates FROM enrichment_results WHERE actor_key=? AND status=?',
                         (actor_key, 'review')).fetchone()
    if not row:
        raise ValueError('No pending review')
    candidates = json.loads(row['candidates'])
    if not 0 <= idx < len(candidates):
        raise ValueError('Invalid candidate')
    return verified_portrait_image(candidates[idx]['url'])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logging.info('%s %s', self.address_string(), fmt % args)

    def is_local(self):
        try:
            return ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            return False

    def valid_host(self):
        """Reject unexpected Host headers to reduce DNS rebinding risks.

        Never use user-provided forwarding headers to determine admin rights.
        """
        header = self.headers.get('Host', '')
        try:
            parsed = urlsplit('http://' + header)
            if (not header or parsed.username or parsed.password or parsed.path or
                    parsed.query or parsed.fragment or parsed.port != PORT):
                return False
            hostname = (parsed.hostname or '').lower().rstrip('.')
            allowed = {'localhost', '127.0.0.1', '::1'}
            allowed.add(self.connection.getsockname()[0].lower())
            allowed.update(x.strip().lower() for x in
                           os.getenv('CAST_EXPLORER_ALLOWED_HOSTS', '').split(',') if x.strip())
            return hostname in allowed
        except (ValueError, AttributeError):
            return False

    def cookie(self, key):
        for entry in self.headers.get('Cookie', '').split(';'):
            name, sep, value = entry.strip().partition('=')
            if sep and name == key:
                return value
        return ''

    def remote_admin_allowed(self):
        return (not self.is_local() and approved_admin_address(self.client_address[0])
                and bool(admin_auth().get('hash')))

    def is_admin(self):
        return self.is_local() or (self.remote_admin_allowed()
                                   and self.logged_in()
                                   and valid_admin_session(self.cookie('cast_admin_session')))

    def logged_in(self):
        if self.is_local():
            return True
        return valid_session(self.cookie('cast_session'))

    def respond(self, status, data, content_type='application/json; charset=utf-8', cache='no-store', extra_headers=()):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', cache)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def redirect(self, path):
        self.respond(302, b'', 'text/plain', extra_headers=(('Location', path),))

    def valid_origin(self):
        """Deny cross-site browser writes, including requests omitting Origin."""
        if self.headers.get('Sec-Fetch-Site', '').lower() in ('cross-site', 'same-site'):
            return False
        origin = self.headers.get('Origin', '')
        if not origin:
            # Only JSON is accepted for POST, so browser forms and no-CORS
            # cross-site fetches cannot use the missing-Origin exception.
            return True
        target = urlsplit(origin)
        host = self.headers.get('Host', '').lower()
        return target.scheme in ('http', 'https') and target.netloc.lower() == host

    def do_GET(self):
        if not self.valid_host():
            return self.respond(400, {'error': 'Unrecognized host'})
        parts = urlsplit(self.path)
        path, params = parts.path, parse_qs(parts.query)
        if path == '/login':
            if self.logged_in():
                return self.redirect('/')
            return self.respond(200, (ASSET_ROOT / 'static' / 'login.html').read_bytes(), 'text/html; charset=utf-8')
        if path == '/api/session':
            return self.respond(200, {'logged_in': self.logged_in(), 'admin': self.is_admin(),
                                      'admin_login_available': self.remote_admin_allowed(),
                                      'password_set': bool(load_auth().get('hash'))})
        if not self.logged_in():
            if path == '/' or path.startswith('/static/'):
                return self.redirect('/login')
            return self.respond(401, {'error': 'Authentication required'})
        try:
            if path == '/admin/login':
                if not self.remote_admin_allowed():
                    return self.respond(403, {'error': 'Remote administration unavailable'})
                if self.is_admin():
                    return self.redirect('/')
                return self.respond(200, (ASSET_ROOT / 'static' / 'admin-login.html').read_bytes(), 'text/html; charset=utf-8')
            if path == '/':
                self.respond(200, (ASSET_ROOT / 'static' / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            elif path == '/static/app.js':
                self.respond(200, (ASSET_ROOT / 'static' / 'app.js').read_bytes(), 'text/javascript; charset=utf-8')
            elif path == '/static/style.css':
                self.respond(200, (ASSET_ROOT / 'static' / 'style.css').read_bytes(), 'text/css; charset=utf-8')
            elif path == '/api/config':
                config = load_config()
                # LAN clients can see that Plex is configured, but never the actual URL or secret.
                self.respond(200, {'url': config['url'] if self.is_admin() else '',
                                   'admin': self.is_admin(),
                                   'admin_login_available': self.remote_admin_allowed(),
                                   'token_set': bool(config['token']), 'version': VERSION})
            elif path == '/api/links':
                server_ip = self.connection.getsockname()[0]
                self.respond(200, plex_link_config(self.client_address[0], server_ip))
            elif path == '/api/art/config':
                if not self.is_admin():
                    return self.respond(403, {'error': 'Server-only settings'})
                art_keys = artwork_keys()
                self.respond(200, {'tmdb_set': bool(art_keys['tmdb']), 'tmdb_enabled': provider_enabled('tmdb'), 'theporndb_set': bool(art_keys['theporndb']), 'wikimedia_enabled': provider_enabled('wikimedia')})
            elif path == '/api/art/search':
                if not self.is_admin():
                    return self.respond(403, {'error': 'Art searches can be started only on the server'})
                self.respond(200, find_art(params.get('key', [''])[0]))
            elif path == '/api/art/preview':
                if not self.is_admin():
                    return self.respond(403, {'error': 'Server-only artwork previews'})
                entry = candidate(params.get('id', [''])[0])
                raw, ext = external_image(entry['url'])
                self.respond(200, raw, {'png':'image/png','jpg':'image/jpeg','webp':'image/webp'}[ext], 'private, max-age=300')
            elif path == '/api/enrich/status':
                if not self.is_admin():
                    return self.respond(403, {'error': 'Server-only artwork administration'})
                self.respond(200, enrichment_status())
            elif path == '/api/enrich/review':
                if not self.is_admin():
                    return self.respond(403, {'error': 'Server-only artwork administration'})
                self.respond(200, {'results': review_enrichment()})
            elif path == '/api/enrich/preview':
                if not self.is_admin():
                    return self.respond(403, {'error': 'Server-only artwork administration'})
                raw, ext = get_enrichment_preview(params.get('key', [''])[0], int(params.get('i', ['-1'])[0]))
                self.respond(200, raw, {'png':'image/png','jpg':'image/jpeg','webp':'image/webp'}[ext], 'private, max-age=120')
            elif path == '/api/status':
                self.respond(200, status_snapshot())
            elif path == '/api/stats':
                self.respond(200, get_stats())
            elif path == '/api/actors':
                self.respond(200, list_actors(params))
            elif path == '/api/actor':
                result = get_actor(params.get('key', [''])[0])
                self.respond(200 if result else 404, result or {'error': 'Actor not found'})
            elif path == '/api/image':
                kind, key = params.get('kind', [''])[0], params.get('key', [''])[0]
                raw = image_bytes(kind, key)
                media_type = 'image/png' if raw.startswith(b'\x89PNG') else ('image/webp' if raw.startswith(b'RIFF') and b'WEBP' in raw[:16] else 'image/jpeg')
                self.respond(200, raw, media_type, 'private, max-age=3600')
            elif path == '/favicon.ico':
                self.respond(204, b'', 'image/png')
            else:
                self.respond(404, {'error': 'Not found'})
        except Exception as exc:
            logging.warning('GET %s failed (%s)', path, type(exc).__name__)
            # Do not expose filesystem paths, provider URLs, or token-bearing
            # library exception details to authenticated LAN browsers.
            status = 404 if path == '/api/image' else 500
            self.respond(status, {'error': 'Image unavailable' if status == 404 else 'Request failed'})

    def do_POST(self):
        if not self.valid_host():
            return self.respond(400, {'error': 'Unrecognized host'})
        parts = urlsplit(self.path)
        path = parts.path
        if not self.valid_origin():
            return self.respond(403, {'error': 'Cross-origin request rejected'})
        # Require a non-simple browser content type to prevent CSRF via HTML
        # forms and no-CORS requests, including loopback auto-admin sessions.
        if self.headers.get('Content-Type', '').split(';', 1)[0].strip().lower() != 'application/json':
            return self.respond(415, {'error': 'Use application/json for API requests'})
        if self.headers.get('Transfer-Encoding'):
            return self.respond(400, {'error': 'Chunked requests not supported'})
        if not self.logged_in() and path != '/api/login':
            return self.respond(401, {'error': 'Authentication required'})
        if path in ('/api/config', '/api/sync', '/api/art/config', '/api/art/apply', '/api/art/remove', '/api/enrich/start', '/api/enrich/stop', '/api/enrich/approve', '/api/enrich/skip', '/api/enrich/reject', '/api/enrich/retry-errors', '/api/enrich/accept-unique') and not self.is_admin():
            return self.respond(403, {'error': 'Server setup and indexing can only be initiated on the Plex server itself.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length > 4096 or length < 0:
                return self.respond(413, {'error': 'Request is too large'})
            data = json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(data, dict):
                return self.respond(400, {'error': 'Invalid request'})
            if path == '/api/login':
                if self.is_local():
                    return self.respond(200, {'ok': True})
                if not load_auth().get('hash'):
                    return self.respond(403, {'error': 'Set a gallery password on the server first.'})
                if not can_try_login(self.client_address[0]):
                    return self.respond(429, {'error': 'Too many failed attempts. Try again in five minutes.'})
                password = data.get('password', '')
                if not isinstance(password, str) or not verify_password(password):
                    record_failed_login(self.client_address[0])
                    return self.respond(401, {'error': 'Incorrect password'})
                session = create_session()
                # SameSite Strict prevents cookies being submitted on cross-origin navigation.
                self.respond(200, {'ok': True}, extra_headers=((
                    'Set-Cookie', f'cast_session={session}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_SECONDS}'
                ),))
            elif path == '/api/logout':
                self.respond(200, {'ok': True}, extra_headers=(
                    ('Set-Cookie', 'cast_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'),
                    ('Set-Cookie', 'cast_admin_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'),
                ))
            elif path == '/api/admin/login':
                if not self.remote_admin_allowed():
                    return self.respond(403, {'error': 'Remote administration unavailable'})
                if not can_try_login('admin:' + self.client_address[0]):
                    return self.respond(429, {'error': 'Too many failed attempts. Try again later.'})
                password = data.get('password', '')
                if not isinstance(password, str) or not verify_admin_password(password):
                    record_failed_login('admin:' + self.client_address[0])
                    return self.respond(401, {'error': 'Invalid administrator password'})
                self.respond(200, {'ok': True}, extra_headers=((
                    'Set-Cookie', f'cast_admin_session={make_admin_session()}; Path=/; HttpOnly; SameSite=Strict; Max-Age={ADMIN_SESSION_SECONDS}'
                ),))
            elif path == '/api/admin/logout':
                self.respond(200, {'ok': True}, extra_headers=((
                    'Set-Cookie', 'cast_admin_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'
                ),))
            elif path == '/api/config':
                url = str(data.get('url', '')).strip().rstrip('/')
                parsed = urlsplit(url)
                if (parsed.scheme not in ('http', 'https') or not parsed.hostname or
                        parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
                    return self.respond(400, {'error': 'Enter a valid Plex server URL, e.g. http://127.0.0.1:32400'})
                token = data.get('token')
                if token is not None and (not isinstance(token, str) or len(token) > 512):
                    return self.respond(400, {'error': 'Invalid token'})
                save_config(url, token or None)
                self.respond(200, {'ok': True})
            elif path == '/api/art/config':
                tmdb = data.get('tmdb', '')
                tpdb = data.get('theporndb', '')
                if not all(isinstance(x, str) and len(x) <= 512 for x in (tmdb, tpdb)):
                    return self.respond(400, {'error': 'Invalid provider token'})
                save_artwork_keys(tmdb.strip(), tpdb.strip())
                self.respond(200, {'ok': True})
            elif path == '/api/art/apply':
                key, identifier = data.get('key', ''), data.get('id', '')
                if not isinstance(key, str) or not isinstance(identifier, str):
                    return self.respond(400, {'error': 'Invalid selection'})
                apply_art(key, identifier)
                self.respond(200, {'ok': True})
            elif path == '/api/art/remove':
                key = data.get('key', '')
                if not isinstance(key, str):
                    return self.respond(400, {'error': 'Invalid performer'})
                remove_art(key)
                self.respond(200, {'ok': True})
            elif path == '/api/enrich/start':
                self.respond(200, {'ok': True, 'started': enrichment_start()})
            elif path == '/api/enrich/stop':
                enrichment_stop()
                self.respond(200, {'ok': True})
            elif path == '/api/enrich/accept-unique':
                self.respond(200, {'ok': True, 'started': review_single_batch_start()})
            elif path == '/api/enrich/retry-errors':
                self.respond(200, {'ok': True, 'reset': retry_enrichment_errors()})
            elif path == '/api/enrich/approve':
                key, number = data.get('key'), data.get('i')
                if not isinstance(key, str) or type(number) is not int:
                    return self.respond(400, {'error': 'Invalid selection'})
                approve_enrichment(key, number)
                self.respond(200, {'ok': True})
            elif path == '/api/enrich/skip':
                key = data.get('key')
                if not isinstance(key, str):
                    return self.respond(400, {'error': 'Invalid selection'})
                skip_enrichment(key)
                self.respond(200, {'ok': True})
            elif path == '/api/enrich/reject':
                key, number = data.get('key'), data.get('i')
                if not isinstance(key, str) or type(number) is not int:
                    return self.respond(400, {'error': 'Invalid selection'})
                remains = reject_enrichment_candidate(key, number)
                self.respond(200, {'ok': True, 'has_more': remains})
            elif path == '/api/sync':
                started = sync_start(force=bool(data.get('force', False)))
                self.respond(200, {'ok': True, 'started': started})
            else:
                self.respond(404, {'error': 'Not found'})
        except Exception:
            logging.exception('POST failed')
            self.respond(500, {'error': 'Request failed'})


def main():
    init_db()
    prune_old_artwork()
    address = f'http://{HOST}:{PORT}'
    print(f'Plex Cast Explorer v{VERSION} — {address}', flush=True)
    print('LAN server listening. Access from other devices at http://SERVER-IP:' + str(PORT), flush=True)
    if not load_auth().get('hash'):
        print('LAN access locked until a gallery password is set. Use the Start Menu: Plex Cast Explorer > Set Gallery Password.', flush=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    # Incremental refresh on startup and every 12 hours by default.
    def background_refresh():
        interval = max(1, float(os.getenv('CAST_EXPLORER_SYNC_HOURS', '12'))) * 3600
        while True:
            prune_old_artwork()
            if load_config()['url'] and load_config()['token']:
                sync_start()
            time.sleep(interval)
    threading.Thread(target=background_refresh, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Stopping...')
    finally:
        server.server_close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--version']:
        print(VERSION)
    elif sys.argv[1:] in (['--set-admin-password'], ['--set-password']):
        import getpass
        admin_mode = sys.argv[1] == '--set-admin-password'
        first = getpass.getpass('New ' + ('administrator' if admin_mode else 'gallery') + ' password: ')
        confirm = getpass.getpass('Confirm password: ')
        if first != confirm:
            raise SystemExit('Passwords do not match.')
        (set_admin_password if admin_mode else set_password)(first)
        print('Password updated; old sessions have been invalidated.')
    elif len(sys.argv) > 1:
        raise SystemExit('Usage: PlexCastExplorer.exe [--set-admin-password | --set-password]')
    else:
        main()
