"""Optional offline IMDb known-for cross-check; never fetches or scrapes IMDb."""
import csv
import gzip
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile


def clean_title(s):
    import unicodedata
    s = unicodedata.normalize('NFKD', str(s or '')).casefold()
    return ' '.join(re.findall(r'[a-z0-9]+', ''.join(c for c in s if not unicodedata.combining(c))))


def tsv_rows(path, fields):
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        if not set(fields).issubset(reader.fieldnames or []):
            raise ValueError('Incorrect IMDb dataset columns')
        yield from reader


def update_index(names_gz, titles_gz, destination):
    """Atomically rebuild filtered IMDb title/known-for index from official TSV.gz files.

    Index stores only known-for title IDs and metadata, no images or bulk IMDb dataset.
    No network access. Existing index survives failed updates.
    """
    names_gz, titles_gz, destination = map(Path, (names_gz, titles_gz, destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix='imdb-update-', suffix='.sqlite', dir=destination.parent)
    os.close(fd)
    temp = Path(temp_name)
    db = None
    try:
        db = sqlite3.connect(temp)
        db.executescript("""CREATE TABLE people(nconst TEXT PRIMARY KEY, name TEXT, known TEXT);
            CREATE TABLE titles(tconst TEXT PRIMARY KEY, title TEXT NOT NULL, year INTEGER);
            CREATE TABLE info(key TEXT PRIMARY KEY, value TEXT NOT NULL);""")
        known_ids = set()
        for row in tsv_rows(names_gz, ('nconst', 'primaryName', 'knownForTitles')):
            ids = [x for x in row['knownForTitles'].split(',') if re.fullmatch(r'tt[0-9]+', x)]
            if not ids:
                continue
            db.execute('INSERT INTO people VALUES(?,?,?)', (row['nconst'], row['primaryName'], ','.join(ids)))
            known_ids.update(ids)
        db.commit()
        for row in tsv_rows(titles_gz, ('tconst', 'primaryTitle', 'startYear')):
            if row['tconst'] not in known_ids:
                continue
            year = int(row['startYear']) if row['startYear'].isdigit() else None
            db.execute('INSERT INTO titles VALUES(?,?,?)', (row['tconst'], clean_title(row['primaryTitle']), year))
        db.execute('INSERT INTO info VALUES(?,?)', ('format', 'imdb-known-for-v1'))
        db.commit()
        db.close()
        db = None
        os.replace(temp, destination)
    finally:
        if db is not None:
            db.close()
        if temp.exists():
            temp.unlink()


def supporting_credits(destination, imdb_id, local_titles):
    """Count exact title/year corroboration; missing known-for data means unknown."""
    if not re.fullmatch(r'nm[0-9]+', str(imdb_id or '')) or not Path(destination).is_file():
        return 0
    local = {(clean_title(x.get('title')), x.get('year')) for x in local_titles}
    with sqlite3.connect(f'file:{Path(destination).resolve().as_posix()}?mode=ro', uri=True) as db:
        person = db.execute('SELECT known FROM people WHERE nconst=?', (imdb_id,)).fetchone()
        if not person:
            return 0
        titles = person[0].split(',')
        if not titles:
            return 0
        found = 0
        for ident in titles:
            row = db.execute('SELECT title,year FROM titles WHERE tconst=?', (ident,)).fetchone()
            if row and any(title == row[0] and year is not None and row[1] == year
                           for title, year in local):
                found += 1
        return found
