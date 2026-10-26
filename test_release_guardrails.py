"""LAN host validation and metadata provider opt-in checks."""
import os
import tempfile
import time
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from http.server import ThreadingHTTPServer

import app


class ReleaseGuardrailTests(unittest.TestCase):
    def test_providers_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(app.provider_enabled('tmdb'))
            self.assertFalse(app.provider_enabled('wikimedia'))

    def test_tmdb_network_boundary_requires_opt_in(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'explicit installer opt-in'):
                app.provider_json('https://api.themoviedb.org/3/search/person?query=example', 'secret')
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                app.provider_json('https://www.wikidata.org/w/api.php', '')

    def test_tmdb_opt_in_requires_explicit_flag(self):
        with patch.dict(os.environ, {'CAST_EXPLORER_ENABLE_TMDB': '1',
                                     'CAST_EXPLORER_ENABLE_WIKIMEDIA': '1',
                                     'CAST_EXPLORER_TMDB_TOKEN': 'example-token'}):
            self.assertTrue(app.provider_enabled('tmdb'))
            self.assertFalse(app.provider_enabled('wikimedia'))
        with patch.dict(os.environ, {'CAST_EXPLORER_ENABLE_TMDB': 'true'}):
            self.assertFalse(app.provider_enabled('tmdb'))

    def test_tmdb_token_can_be_saved_without_automatically_enabling_lookup(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, 'ART_CONFIG_PATH', Path(tmp) / 'artwork.json'):
            app.save_artwork_keys('new-tmdb-token', 'tpdb-token')
            keys = app.artwork_keys()
            self.assertEqual(keys['tmdb'], 'new-tmdb-token')
            self.assertEqual(keys['theporndb'], 'tpdb-token')
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(app.provider_enabled('tmdb'))

    def test_tmdb_image_uses_high_resolution_with_fallback(self):
        with patch.object(app, 'external_image', return_value=(b'img', 'jpg')) as image:
            self.assertEqual(app.verified_portrait_image('https://image.tmdb.org/t/p/w342/x.jpg'), (b'img', 'jpg'))
            image.assert_called_once_with('https://image.tmdb.org/t/p/h632/x.jpg')
        with patch.object(app, 'external_image', side_effect=[ValueError('Unavailable'), (b'fallback', 'jpg')]) as image:
            self.assertEqual(app.verified_portrait_image('https://image.tmdb.org/t/p/w342/x.jpg'), (b'fallback', 'jpg'))
            self.assertEqual(image.call_count, 2)

    def test_privacy_notice_accessible_without_authentication(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        old_port = app.PORT
        app.PORT = server.server_port
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with urlopen(f'http://127.0.0.1:{server.server_port}/privacy', timeout=3) as response:
                text = response.read().decode('utf-8')
                self.assertEqual(response.status, 200)
                self.assertIn('Privacy &amp; Legal', text)
                self.assertIn('ThePornDB', text)
                self.assertIn('not affiliated', text)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
            app.PORT = old_port

    def test_untrusted_host_header_rejected(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        old_port = app.PORT
        app.PORT = server.server_port
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/api/session'
            with urlopen(url, timeout=3) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b'"admin": true', response.read())
            with self.assertRaises(HTTPError) as exc:
                urlopen(Request(url, headers={'Host': f'evil.example:{server.server_port}'}), timeout=3)
            self.assertEqual(exc.exception.code, 400)
            with self.assertRaises(HTTPError) as exc:
                urlopen(Request(url.replace('/api/session', '/api/login'), method='POST',
                                data=b'{}', headers={'Origin': 'http://evil.example'}), timeout=3)
            self.assertEqual(exc.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
            app.PORT = old_port


    def test_csrf_and_post_content_type_guards(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        old_port = app.PORT
        app.PORT = server.server_port
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}/api/login'
            for headers, expected in (
                ({'Content-Type': 'text/plain'}, 415),
                ({'Content-Type': 'application/json', 'Sec-Fetch-Site': 'cross-site'}, 403),
                ({'Content-Type': 'application/json', 'Transfer-Encoding': 'chunked'}, 400),
            ):
                with self.subTest(headers=headers):
                    request = Request(base, method='POST', data=b'{}', headers=headers)
                    with self.assertRaises(HTTPError) as error:
                        urlopen(request, timeout=3)
                    self.assertEqual(error.exception.code, expected)
            with urlopen(Request(base, method='POST', data=b'{}',
                                 headers={'Content-Type': 'application/json'}), timeout=3) as response:
                self.assertEqual(response.status, 200)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
            app.PORT = old_port

    def test_tmdb_cache_expires_but_other_portraits_remain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_db, old_dir = app.DB_PATH, app.PORTRAIT_DIR
            app.DB_PATH = Path(tmpdir) / 'cache.db'
            app.PORTRAIT_DIR = Path(tmpdir) / 'portraits'
            app.PORTRAIT_DIR.mkdir()
            try:
                app.init_db()
                now = time.time()
                old_timestamp = int((now - 181 * 86400) * 1000)
                images = [('tmdb-old', 'TMDB', old_timestamp),
                          ('tmdb-new', 'TMDB', int(now * 1000)),
                          ('plex-file', 'Plex', old_timestamp)]
                with app.db_open() as db:
                    for key, source, timestamp in images:
                        file = key.encode().hex().ljust(64, '0') + '.jpg'
                        (app.PORTRAIT_DIR / file).write_bytes(b'portrait')
                        db.execute('INSERT INTO actor_art(actor_key,file,source,version) VALUES(?,?,?,?)',
                                   (key, file, source, timestamp))
                    db.execute('INSERT INTO enrichment_results(actor_key,status,checked_at) VALUES(?,?,?)',
                               ('expired', 'review', '2025-01-01T00:00:00+00:00'))
                self.assertEqual(app.prune_old_artwork(now), 1)
                with app.db_open() as db:
                    rows = db.execute('SELECT actor_key FROM actor_art ORDER BY actor_key').fetchall()
                    self.assertEqual([row[0] for row in rows], ['plex-file', 'tmdb-new'])
                    self.assertEqual(db.execute('SELECT count(*) FROM enrichment_results').fetchone()[0], 0)
                self.assertEqual(len(list(app.PORTRAIT_DIR.glob('*.jpg'))), 2)
            finally:
                app.DB_PATH, app.PORTRAIT_DIR = old_db, old_dir
                app.image_bytes.cache_clear()


if __name__ == '__main__':
    unittest.main()
