"""Offline IMDb dataset update/identity regressions."""
import gzip
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import imdb_identity


def sample(path, data):
    with gzip.open(path, 'wt', encoding='utf-8') as out:
        out.write(data)


class IMDbIndexTests(unittest.TestCase):
    def test_update_replaces_index_and_supports_known_for_credit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            people, titles, index = root / 'name.basics.tsv.gz', root / 'title.basics.tsv.gz', root / 'imdb.sqlite'
            sample(people, 'nconst\tprimaryName\tknownForTitles\n'
                           'nm123\tExample Actor\ttt42,tt99\n'
                           'nm456\tOther Actor\ttt100\n')
            sample(titles, 'tconst\tprimaryTitle\tstartYear\n'
                          'tt42\tFilm Alpha\t2024\n'
                          'tt99\tAnother Title\t2018\n'
                          'tt100\tOther Film\t2024\n')
            imdb_identity.update_index(people, titles, index)
            self.assertEqual(imdb_identity.supporting_credits(index, 'nm123', [
                {'title': 'Film Alpha', 'year': 2024}]), 1)
            # Windows refuses to move/delete a SQLite database whose read
            # connection remains open. Verify a lookup releases its handle.
            moved = root / 'moved.sqlite'
            index.replace(moved)
            moved.replace(index)
            self.assertEqual(imdb_identity.supporting_credits(index, 'nm456', [
                {'title': 'Film Alpha', 'year': 2024}]), 0)
            self.assertEqual(imdb_identity.supporting_credits(index, 'nm123', [
                {'title': 'Film Alpha', 'year': 2019}]), 0)
            sample(titles, 'wrong\tcolumns\n')
            with self.assertRaises(ValueError):
                imdb_identity.update_index(people, titles, index)
            self.assertEqual(imdb_identity.supporting_credits(index, 'nm123', [
                {'title': 'Film Alpha', 'year': 2024}]), 1)


if __name__ == '__main__':
    unittest.main()
