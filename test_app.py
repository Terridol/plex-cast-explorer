"""Run with: python -m unittest test_app.py -v"""
import tempfile
import io
import json
import os
import ipaddress
import unittest
import socket
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch
import xml.etree.ElementTree as ET
import app


class PlexCastExplorerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db = app.DB_PATH
        self.old_conf = app.CONFIG_PATH
        self.old_portraits = app.PORTRAIT_DIR
        self.old_plex_portraits = app.PLEX_PORTRAIT_DIR
        self.old_art_config = app.ART_CONFIG_PATH
        self.old_network_config = app.NETWORK_CONFIG_PATH
        app.DB_PATH = Path(self.temp.name) / 'data.sqlite'
        app.CONFIG_PATH = Path(self.temp.name) / 'settings.json'
        app.PORTRAIT_DIR = Path(self.temp.name) / 'portraits'
        app.PLEX_PORTRAIT_DIR = Path(self.temp.name) / 'plex-portraits'
        app.ART_CONFIG_PATH = Path(self.temp.name) / 'artwork.json'
        app.NETWORK_CONFIG_PATH = Path(self.temp.name) / 'network.json'
        app.image_bytes.cache_clear()
        app.init_db()

    def tearDown(self):
        app.DB_PATH = self.old_db
        app.CONFIG_PATH = self.old_conf
        app.PORTRAIT_DIR = self.old_portraits
        app.PLEX_PORTRAIT_DIR = self.old_plex_portraits
        app.ART_CONFIG_PATH = self.old_art_config
        app.NETWORK_CONFIG_PATH = self.old_network_config
        app.image_bytes.cache_clear()
        self.temp.cleanup()

    def fake_xml(self, path):
        if path == '/':
            return ET.fromstring('<MediaContainer machineIdentifier="abc123"/>')
        if path == '/library/sections':
            return ET.fromstring('''<MediaContainer><Directory key="1" title="Movies" type="movie"/>
                <Directory key="2" title="Series" type="show"/></MediaContainer>''')
        if '/sections/1/all' in path:
            return ET.fromstring('''<MediaContainer totalSize="2"><Video ratingKey="101" updatedAt="123"/>
               <Video ratingKey="102" updatedAt="123"/></MediaContainer>''')
        if '/sections/2/all' in path:
            return ET.fromstring('''<MediaContainer totalSize="1"><Directory ratingKey="201" updatedAt="123"/></MediaContainer>''')
        if path == '/library/metadata/101':
            return ET.fromstring('''<MediaContainer><Video ratingKey="101" title="Alpha" year="2024" thumb="/thumb/101" updatedAt="123">
                <Role tag="Sample Actor" role="Detective" thumb="/portrait/sample"/>
                <Role tag="Second Actor" role="Villain" /></Video></MediaContainer>''')
        if path == '/library/metadata/102':
            return ET.fromstring('''<MediaContainer><Video ratingKey="102" title="Beta" year="2018" updatedAt="123">
                <Role tag="SAMPLE ACTOR" role="Hero"/></Video></MediaContainer>''')
        if path == '/library/metadata/201':
            return ET.fromstring('''<MediaContainer><Directory ratingKey="201" title="Series 1" year="2022" updatedAt="123">
                <Role tag="Sample Actor" role="Officer"/></Directory></MediaContainer>''')
        raise AssertionError('Unexpected Plex request '+path)

    def test_sync_continues_after_short_plex_page(self):
        def short_pages(path):
            if '/sections/1/all' in path:
                from urllib.parse import parse_qs, urlsplit
                offset = int(parse_qs(urlsplit(path).query).get('X-Plex-Container-Start', ['0'])[0])
                ids = ['101'] if offset == 0 else ['102'] if offset == 1 else []
                return ET.fromstring('<MediaContainer totalSize="2">' +
                    ''.join(f'<Video ratingKey="{key}" updatedAt="123"/>' for key in ids) +
                    '</MediaContainer>')
            return self.fake_xml(path)
        with patch.object(app, 'plex_xml', side_effect=short_pages):
            app.sync_all(force=True)
        self.assertEqual(app.status_snapshot()['phase'], 'Finished')
        self.assertEqual(app.get_stats()['titles'], 3)

    def test_sync_refuses_truncated_plex_pages_without_pruning(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        def truncated(path):
            if '/sections/1/all' in path:
                return ET.fromstring('<MediaContainer totalSize="2"/>')
            return self.fake_xml(path)
        with patch.object(app, 'plex_xml', side_effect=truncated):
            app.sync_all(force=False)
        self.assertEqual(app.status_snapshot()['phase'], 'Sync failed')
        self.assertEqual(app.get_stats()['titles'], 3)

    def test_sync_refuses_duplicate_plex_page_items(self):
        def duplicate(path):
            if '/sections/1/all' in path:
                return ET.fromstring('<MediaContainer totalSize="2"><Video ratingKey="101"/><Video ratingKey="101"/></MediaContainer>')
            return self.fake_xml(path)
        with patch.object(app, 'plex_xml', side_effect=duplicate):
            app.sync_all(force=True)
        self.assertEqual(app.status_snapshot()['phase'], 'Sync failed')

    def test_cross_library_index_and_incremental(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml) as mock_plex:
            app.sync_all(force=True)
            self.assertEqual(app.status_snapshot()['phase'], 'Finished')
            stats = app.get_stats()
            self.assertEqual((stats['actors'], stats['titles'], stats['credits']), (2, 3, 4))
            self.assertEqual(stats['machine_id'], 'abc123')
            person = app.get_actor('sample actor')
            self.assertEqual(len(person['titles']), 3)
            self.assertEqual({t['library'] for t in person['titles']}, {'Movies', 'Series'})
            self.assertEqual(app.list_actors({})['total'], 2)
            self.assertEqual(app.list_actors({'search':['Sample']})['total'], 1)
            self.assertEqual(app.list_actors({'search':['Sam%']})['total'], 0)
            self.assertEqual(app.list_actors({'type':['show']})['total'], 1)
            self.assertEqual(app.list_actors({'section':['1']})['total'], 2)
            self.assertEqual(app.list_actors({'sort':['count']})['results'][0]['name'], 'Sample Actor')
            count = mock_plex.call_count
            app.sync_all(force=False)
            self.assertEqual(app.status_snapshot()['phase'], 'Finished')
            self.assertEqual(mock_plex.call_count - count, 4)  # root, sections, 2 paged lists; no detail requests


    def test_normal_sync_does_not_bulk_cache_plex_portraits(self):
        with patch.dict(os.environ, {'CAST_EXPLORER_BULK_PLEX_CACHE': ''}, clear=True), \
             patch.object(app, 'plex_xml', side_effect=self.fake_xml), \
             patch.object(app, 'cache_plex_portraits') as bulk, \
             patch.object(app, 'request_plex') as photo:
            app.sync_all(force=True)
            bulk.assert_not_called()
            photo.assert_not_called()
            self.assertEqual(app.status_snapshot()['phase'], 'Finished')

    def test_sync_downloads_and_reuses_plex_actor_portraits(self):
        # Plex's Role.thumb may be available even though the first sync only
        # indexed its URL. Cache missing images while indexing, and backfill
        # without requiring the movie's updatedAt timestamp to change.
        with patch.dict(os.environ, {'CAST_EXPLORER_BULK_PLEX_CACHE': '1'}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'example-token')
            with patch.object(app, 'plex_xml', side_effect=self.fake_xml), \
                 patch.object(app, 'request_plex', return_value=b'\xff\xd8\xffPlex image') as photo:
                app.sync_all(force=True)
                self.assertEqual(app.status_snapshot()['phase'], 'Finished')
                cache_path = app.plex_portrait_cache_path('/portrait/sample')
                self.assertTrue(cache_path.is_file())
                self.assertEqual(cache_path.read_bytes(), b'\xff\xd8\xffPlex image')
                photo.assert_called_once_with('/portrait/sample', timeout=12,
                                              max_bytes=app.MAX_PLEX_IMAGE_BYTES)
                app.image_bytes.cache_clear()
                self.assertEqual(app.image_bytes('actor', 'sample actor'), b'\xff\xd8\xffPlex image')
                self.assertEqual(photo.call_count, 1)
                app.sync_all(force=False)
                self.assertEqual(photo.call_count, 1)
                self.assertEqual(app.status_snapshot()['phase'], 'Finished')
                self.assertEqual(app.get_actor('second actor')['image'], '')

    def test_sync_repairs_corrupt_plex_actor_cache(self):
        with patch.dict(os.environ, {'CAST_EXPLORER_BULK_PLEX_CACHE': '1'}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'example-token')
            self.assertEqual(app.load_config(), {'url': 'http://127.0.0.1:32400', 'token': 'example-token'})
            path = app.plex_portrait_cache_path('/portrait/sample')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'not an image')
            with patch.object(app, 'plex_xml', side_effect=self.fake_xml), \
                 patch.object(app, 'request_plex', return_value=b'\xff\xd8\xffRecovered') as image_request:
                app.sync_all(force=True)
                image_request.assert_called_once()
                self.assertEqual(path.read_bytes(), b'\xff\xd8\xffRecovered')
                self.assertEqual(app.status_snapshot()['phase'], 'Finished')

    def test_plex_sync_portrait_download_failure_is_non_destructive_and_retryable(self):
        with patch.dict(os.environ, {'CAST_EXPLORER_BULK_PLEX_CACHE': '1'}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'example-token')
            with patch.object(app, 'plex_xml', side_effect=self.fake_xml), \
                 patch.object(app, 'request_plex', side_effect=[OSError('temporarily offline'),
                                                               b'\xff\xd8\xffRecovered']):
                app.sync_all(force=True)
                self.assertEqual(app.status_snapshot()['phase'], 'Finished with warnings')
                self.assertEqual(app.get_stats()['actors'], 2)
                app.sync_all(force=False)
                self.assertEqual(app.status_snapshot()['phase'], 'Finished')
                self.assertTrue(app.plex_portrait_cache_path('/portrait/sample').is_file())

    def test_plex_sync_treats_http_404_as_missing_art_not_sync_error(self):
        with patch.dict(os.environ, {'CAST_EXPLORER_BULK_PLEX_CACHE': '1'}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'test-token')
            missing = HTTPError('https://portrait.example.invalid/?X-Plex-Token=private',
                                404, 'Not Found', {}, None)
            with patch.object(app, 'plex_xml', side_effect=self.fake_xml), \
                 patch.object(app, 'cached_plex_portrait', side_effect=missing) as image:
                app.sync_all(force=True)
                snap = app.status_snapshot()
                self.assertEqual(snap['phase'], 'Finished', snap)
                self.assertEqual(snap['errors'], 0)
                self.assertEqual(snap['portrait_missing'], 1)
                self.assertEqual(snap['portrait_downloaded'], 0)
                self.assertEqual(snap['portrait_failed'], 0)
                self.assertIn('HTTP 404', snap['last_error'])
                self.assertIn('Plex internal', snap['last_error'])
                self.assertNotIn('private', snap['last_error'])
                image.assert_called_once_with('/portrait/sample')
                self.assertEqual(app.get_stats()['actors'], 2)

    def test_plex_sync_reports_http_403_with_live_error_count(self):
        with patch.dict(os.environ, {'CAST_EXPLORER_BULK_PLEX_CACHE': '1'}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'test-token')
            denied = HTTPError('https://example.invalid/private?token=private',
                               403, 'Forbidden', {}, None)
            with patch.object(app, 'plex_xml', side_effect=self.fake_xml), \
                 patch.object(app, 'cached_plex_portrait', side_effect=denied), \
                 patch.object(app, 'state_update', wraps=app.state_update) as state:
                app.sync_all(force=True)
                snap = app.status_snapshot()
                self.assertEqual(snap['phase'], 'Finished with warnings', snap)
                self.assertEqual(snap['errors'], 1)
                self.assertEqual(snap['portrait_failed'], 1)
                self.assertEqual(snap['portrait_missing'], 0)
                self.assertIn('HTTP 403', snap['last_error'])
                self.assertNotIn('private', snap['last_error'])
                self.assertTrue(any(call.kwargs.get('portrait_failed') == 1 and
                                    call.kwargs.get('errors') == 1
                                    for call in state.call_args_list))

    def test_plex_image_source_diagnostics_never_expose_urls_or_tokens(self):
        sources = {
            '/library/metadata/101/thumb?token=private': 'Plex internal',
            'http://127.0.0.1:32400/actor.jpg?token=private': 'Plex server',
            'https://metadata-static.plex.tv/p.jpg?token=private': 'Plex CDN',
            'https://cdn.custom-provider.org/p.jpg?token=private': 'custom scraper',
        }
        with patch.object(app, 'load_config', return_value={
            'url': 'http://127.0.0.1:32400', 'token': 'private'}):
            for thumb, expected in sources.items():
                with self.subTest(expected=expected):
                    label = app.plex_portrait_source_label(thumb)
                    self.assertEqual(label, expected)
                    self.assertNotIn('private', label)
                    self.assertNotIn('http', label)

    def test_plex_sync_pauses_on_http_429_rate_limit(self):
        with patch.dict(os.environ, {'CAST_EXPLORER_BULK_PLEX_CACHE': '1'}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'test-token')
            throttled = HTTPError('https://example.invalid/portrait',
                                  429, 'Too Many Requests', {}, None)
            with patch.object(app, 'plex_xml', side_effect=self.fake_xml), \
                 patch.object(app, 'cached_plex_portrait', side_effect=throttled):
                app.sync_all(force=True)
                snap = app.status_snapshot()
                self.assertEqual(snap['phase'], 'Finished with warnings', snap)
                self.assertEqual(snap['errors'], 1)
                self.assertIn('HTTP 429 (rate limited)', snap['last_error'])

    def test_plex_cdn_403_breaker_skips_only_failing_origin(self):
        # One broken Plex metadata CDN must not block another approved CDN.
        # The failure source URL may include secrets; never surface it.
        with patch.dict(os.environ, {}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'example-token')
            with app.db_open() as db:
                for i in range(60):
                    db.execute('INSERT INTO actors(actor_key,name,thumb) VALUES (?,?,?)',
                               (f'denied-{i}', f'Denied {i}',
                                f'https://metadata-static.plex.tv/people/{i}.jpg'))
                for i in range(2):
                    db.execute('INSERT INTO actors(actor_key,name,thumb) VALUES (?,?,?)',
                               (f'ok-{i}', f'Allowed {i}',
                                f'https://assets.plex.tv/people/{i}.jpg'))
                db.execute('INSERT INTO actors(actor_key,name,thumb) VALUES (?,?,?)',
                           ('later-missing', 'Later missing',
                            'https://zz-custom.invalid-example.org/missing.jpg'))
            requests = []
            def fake_image(thumb):
                requests.append(thumb)
                if 'metadata-static.plex.tv' in thumb:
                    raise HTTPError(thumb + '?token=secret', 403, 'Forbidden', {}, None)
                if 'zz-custom.invalid-example.org' in thumb:
                    raise HTTPError(thumb, 404, 'Not Found', {}, None)
                return b'\xff\xd8\xffDownloaded'
            app.state_update(errors=0, last_error='')
            with patch.object(app, 'cached_plex_portrait', side_effect=fake_image):
                count = app.cache_plex_portraits()
            state = app.status_snapshot()
            self.assertEqual(count, 25, state)
            self.assertEqual(state['portrait_downloaded'], 2, state)
            self.assertEqual(state['portrait_failed'], 25, state)
            self.assertEqual(state['portrait_missing'], 1, state)
            self.assertEqual(state['portrait_skipped'], 35, state)
            self.assertEqual(state['total'], 63, state)
            self.assertEqual(state['current'], 28, state)
            self.assertEqual(len(requests), 28)
            self.assertEqual(len([x for x in requests if 'assets.plex.tv' in x]), 2)
            self.assertIn('Plex CDN', state['last_error'])
            self.assertIn('HTTP 403', state['last_error'])
            self.assertNotIn('HTTP 404', state['last_error'])
            self.assertNotIn('secret', state['last_error'])
            self.assertNotIn('metadata-static.plex.tv', state['last_error'])

    def test_large_portrait_source_samples_across_entire_index(self):
        portraits = [f'/portrait/{i:05d}' for i in range(50000)]
        spread = app.spread_plex_portrait_probes(portraits)
        self.assertEqual(len(spread), len(portraits))
        self.assertEqual(set(spread), set(portraits))
        # First 25 requests span the large set instead of the first 25 IDs.
        self.assertGreater(int(spread[24].rsplit('/', 1)[-1]), 40000)

    def test_mixed_403_portraits_do_not_skip_working_same_origin(self):
        with patch.dict(os.environ, {}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'example-token')
            with app.db_open() as db:
                for i in range(200):
                    db.execute('INSERT INTO actors(actor_key,name,thumb) VALUES (?,?,?)',
                               (f'actor-{i}', f'Actor {i}',
                                f'https://metadata-static.plex.tv/images/{i:05d}.jpg'))
            observed = []
            def fake_image(thumb):
                observed.append(thumb)
                n = int(thumb.rsplit('/', 1)[-1].split('.')[0])
                if n < 40:
                    raise HTTPError(thumb + '?token=secret', 403, 'Forbidden', {}, None)
                return b'\xff\xd8\xffOK'
            app.state_update(errors=0, last_error='')
            with patch.object(app, 'cached_plex_portrait', side_effect=fake_image):
                failures = app.cache_plex_portraits()
            status = app.status_snapshot()
            self.assertEqual(failures, 40, status)
            self.assertEqual(status['portrait_skipped'], 0, status)
            self.assertEqual(status['portrait_downloaded'], 160, status)
            self.assertEqual(status['current'], 200, status)
            self.assertEqual(len(observed), 200)

    def test_known_plex_cdn_http_403_retries_authenticated_plex_transcode(self):
        thumb = 'https://metadata-static.plex.tv/people/image.jpg'
        blocked = HTTPError(thumb, 403, 'Forbidden', {}, None)
        with patch.object(app, 'build_opener') as opener, \
             patch.object(app, 'plex_transcoded_image',
                          return_value=b'\xff\xd8\xffPlex') as transcoder:
            opener.return_value.open.side_effect = blocked
            self.assertEqual(app.plex_image_bytes(thumb), b'\xff\xd8\xffPlex')
            transcoder.assert_called_once_with(thumb)
            direct = opener.return_value.open.call_args.args[0]
            self.assertNotIn('X-Plex-Token', direct.headers)

    def test_failed_plex_transcode_keeps_original_403_diagnostic(self):
        thumb = 'https://metadata-static.plex.tv/people/image.jpg'
        direct_403 = HTTPError(thumb, 403, 'Forbidden', {}, None)
        plex_404 = HTTPError('http://plex.invalid/photo/:/transcode',
                             404, 'Not Found', {}, None)
        with patch.object(app, 'build_opener') as opener, \
             patch.object(app, 'plex_transcoded_image', side_effect=plex_404):
            opener.return_value.open.side_effect = direct_403
            with self.assertRaises(HTTPError) as caught:
                app.plex_image_bytes(thumb)
            self.assertEqual(caught.exception.code, 403)

    def test_plex_sync_never_replaces_manual_portrait_override(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        candidate = app.new_art_candidate('sample actor', 'Sample Actor',
            'https://image.tmdb.org/t/p/w342/img.jpg', 'TMDB',
            'https://www.themoviedb.org/person/12', 'TMDB')
        with patch.object(app, 'external_image', return_value=(b'\xff\xd8\xffManual','jpg')):
            app.apply_art('sample actor', candidate['id'])
        with patch.dict(os.environ, {}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'example-token')
            with patch.object(app, 'plex_xml', side_effect=self.fake_xml), \
                 patch.object(app, 'request_plex') as image_request:
                app.sync_all(force=False)
                image_request.assert_not_called()
        self.assertEqual(app.image_bytes('actor', 'sample actor'), b'\xff\xd8\xffManual')
        self.assertEqual(app.get_actor('sample actor')['art']['source'], 'TMDB')

    def test_plex_image_retrieval_limits_bytes_and_prevents_external_hosts(self):
        with patch.object(app, 'load_config', return_value={'url':'http://127.0.0.1:32400','token':'example'}), \
             patch.object(app, 'request_plex', return_value=b'\xff\xd8\xffimage') as request:
            self.assertEqual(app.plex_image_bytes('http://127.0.0.1:32400/portrait/2'),
                             b'\xff\xd8\xffimage')
            request.assert_called_once_with('/portrait/2', timeout=12,
                                             max_bytes=app.MAX_PLEX_IMAGE_BYTES)
            with self.assertRaisesRegex(ValueError, 'public HTTPS'):
                app.plex_image_bytes('https://untrusted.example/portrait.jpg')
            with self.assertRaisesRegex(ValueError, 'public HTTPS'):
                app.plex_image_bytes('http://untrusted.example/portrait.jpg')

    def test_custom_scraper_https_role_thumb_is_fetched_through_plex(self):
        custom_url = 'https://cdn.custom-actor-images.org/actors/sample.jpg'
        def custom_xml(path):
            item = self.fake_xml(path)
            if path == '/library/metadata/101':
                # Plex metadata responses are MediaContainer -> Video -> Role.
                # A direct find('Role') returns None and makes the sync report
                # an indexing warning instead of exercising image retrieval.
                role = item.find('./Video/Role')
                self.assertIsNotNone(role, 'Expected Plex cast Role inside Video')
                role.set('thumb', custom_url)
            return item
        # Test image-transcoding and caching independently of the DNS guard.
        # Public/private hostname decisions have their own deterministic tests.
        # The source URL still must reach the eligibility gate before Plex.
        with patch.dict(os.environ, {}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'example-token')
            with patch.object(app, 'plex_xml', side_effect=custom_xml), \
                 patch.object(app, 'public_custom_plex_thumb', return_value=True) as approved, \
                 patch.object(app, 'request_plex',
                              return_value=b'\xff\xd8\xffCustom') as plex:
                app.sync_all(force=True)
                self.assertEqual(app.status_snapshot()['phase'], 'Finished',
                                 app.status_snapshot())
                approved.assert_not_called()
                plex.assert_not_called()
                # Portraits are fetched only when the gallery requests them.
                app.image_bytes.cache_clear()
                self.assertEqual(app.image_bytes('actor', 'sample actor'),
                                 b'\xff\xd8\xffCustom')
                approved.assert_called_once_with(custom_url)
                plex.assert_called_once()
                proxied = plex.call_args.args[0]
                self.assertTrue(proxied.startswith('/photo/:/transcode?'))
                self.assertEqual(parse_qs(urlsplit(proxied).query)['url'], [custom_url])
                self.assertNotIn('X-Plex-Token', proxied)
                self.assertEqual(plex.call_args.kwargs['max_bytes'],
                                 app.MAX_PLEX_IMAGE_BYTES)
                plex.assert_called_once()

    def test_private_custom_scraper_image_is_not_proxied_through_plex(self):
        urls = ('http://192.168.1.20:3000/actors/a.jpg',
                'https://127.0.0.1/photo.jpg',
                'https://actor-images.local/photo.jpg',
                'https://actor-images.example/photo.jpg',
                'https://user:password@cdn.example.org/actor.jpg')
        with patch.object(app, 'request_plex') as plex:
            for url in urls:
                with self.subTest(url=url):
                    with self.assertRaisesRegex(ValueError, 'public HTTPS'):
                        app.plex_image_bytes(url)
            plex.assert_not_called()

    def test_custom_scraper_public_dns_accepts_only_global_addresses(self):
        url = 'https://cdn.custom-actor-images.org/actors/sample.jpg'
        resolved = [(socket.AF_INET, socket.SOCK_STREAM, 6, '',
                     ('8.8.8.8', 443))]
        with patch.object(app.socket, 'getaddrinfo', return_value=resolved) as dns:
            self.assertTrue(app.public_custom_plex_thumb(url))
            dns.assert_called_once_with('cdn.custom-actor-images.org', 443,
                                        type=socket.SOCK_STREAM)

    def test_custom_scraper_dns_must_resolve_only_public_addresses(self):
        url = 'https://cdn.custom-actor-images.org/actors/sample.jpg'
        cases = (
            [('192.168.1.50', 443)],
            [('93.184.216.34', 443), ('10.0.0.9', 443)],
            [('::1', 443)],
        )
        for targets in cases:
            resolved = [(socket.AF_INET6 if ':' in addr else socket.AF_INET,
                         socket.SOCK_STREAM, 6, '', (addr, port)) for addr, port in targets]
            with self.subTest(targets=targets), \
                 patch.object(app.socket, 'getaddrinfo', return_value=resolved), \
                 patch.object(app, 'request_plex') as plex:
                with self.assertRaisesRegex(ValueError, 'public HTTPS'):
                    app.plex_image_bytes(url)
                plex.assert_not_called()

    def test_custom_scraper_metadata_bundle_role_portrait(self):
        # Plex's custom/NFO agents can supply metadata:// or media:// URLs
        # instead of an ordinary HTTPS CDN or library/metadata thumb path.
        role = ET.Element('Role', {'tag': 'Sample Actor', 'role': 'Hero',
                                  'thumb': 'metadata://posters/people/sample.jpg'})
        self.assertEqual(app.plex_role_thumb(role, '101'),
                         '/library/metadata/101/file?url=metadata%3A%2F%2Fposters%2Fpeople%2Fsample.jpg')
        role.set('thumb', 'media://photos/people/sample.png')
        self.assertIn('/library/metadata/101/file?url=media%3A%2F%2F',
                      app.plex_role_thumb(role, '101'))
        self.assertEqual(app.plex_role_thumb(role, '../../private'), '')

    def test_plex_role_key_resolves_person_portrait_through_plex(self):
        # A third-party agent may provide Role.key without Role.thumb. When
        # Plex's own person metadata advertises a thumb, retrieve through Plex.
        def plex_metadata(path):
            if path == '/library/metadata/person-223':
                return ET.fromstring('<MediaContainer><Directory thumb="media://people/portrait.png"/></MediaContainer>')
            if path == '/library/metadata/101':
                return ET.fromstring(
                    '<MediaContainer><Video ratingKey="101" title="Alpha" year="2024" updatedAt="123">'
                    '<Role tag="Sample Actor" thumb="/portrait/sample"/>'
                    '<Role tag="Second Actor" key="/library/metadata/person-223"/>'
                    '</Video></MediaContainer>')
            return self.fake_xml(path)
        with patch.dict(os.environ, {}, clear=True):
            app.save_config('http://127.0.0.1:32400', 'example-token')
            with patch.object(app, 'plex_xml', side_effect=plex_metadata), \
                 patch.object(app, 'request_plex', return_value=b'\xff\xd8\xffPlex person') as requests:
                app.sync_all(force=True)
                self.assertEqual(app.status_snapshot()['phase'], 'Finished')
                person = app.get_actor('second actor')
                self.assertEqual(person['art']['source'], 'Plex')
                self.assertEqual(app.image_bytes('actor', 'second actor'), b'\xff\xd8\xffPlex person')
                paths = [call.args[0] for call in requests.call_args_list]
                self.assertTrue(any(p.startswith('/library/metadata/person-223/file?url=media%3A%2F%2F')
                                    for p in paths), paths)
                requests.reset_mock()
                app.sync_all(force=False)
                requests.assert_not_called()

    def test_plex_role_metadata_key_rejects_non_plex_paths(self):
        for value in ('http://attacker.example/actor', '//evil.example/portrait',
                      '/library/metadata/../../settings', '/library/metadata/1/children',
                      '/library/metadata/', '/library/metadata/1?foo=1'):
            with self.subTest(path=value):
                role = ET.Element('Role', {'key': value})
                self.assertEqual(app.plex_role_metadata_path(role), '')
        role = ET.Element('Role', {'ratingKey': 'person-id_123'})
        self.assertEqual(app.plex_role_metadata_path(role),
                         '/library/metadata/person-id_123')

    def test_provider_json_reads_large_valid_credit_payload_without_truncating(self):
        # Regression: ThePornDB sometimes returns scene-credit JSON larger
        # than 1,000,001 bytes; older code truncated it mid-string.
        payload = {'data': [{'title': 'Scene ' + ('x' * 1_050_000)}]}
        body = json.dumps(payload).encode('utf-8')
        self.assertGreater(len(body), 1_000_001)
        self.assertLess(len(body), app.MAX_PROVIDER_JSON_BYTES)
        with patch.object(app, 'build_opener') as opener:
            opener.return_value.open.return_value = io.BytesIO(body)
            actual = app.provider_json('https://api.theporndb.net/performers/123/scenes?page=1&per_page=100', 'sample-token')
        self.assertEqual(actual, payload)

    def test_provider_json_rejects_oversized_payload_before_parsing(self):
        # Reject huge/malicious metadata rather than parsing an incomplete
        # buffer and reporting a confusing JSON error.
        oversized = b'x' * (app.MAX_PROVIDER_JSON_BYTES + 1)
        with patch.object(app, 'build_opener') as opener:
            opener.return_value.open.return_value = io.BytesIO(oversized)
            with self.assertRaisesRegex(ValueError, '8 MiB safety limit'):
                app.provider_json('https://api.theporndb.net/performers/123/scenes?page=1&per_page=100', 'sample-token')

    def test_provider_json_rejects_empty_metadata_response(self):
        with patch.object(app, 'build_opener') as opener:
            opener.return_value.open.return_value = io.BytesIO(b'')
            with self.assertRaisesRegex(ValueError, 'empty response'):
                app.provider_json('https://api.theporndb.net/performers?q=sample', 'sample-token')

    def test_local_and_remote_links(self):
        known = (ipaddress.ip_network('10.44.10.0/24'), ipaddress.ip_network('192.168.77.0/24'))
        with patch.object(app, 'lan_networks', return_value=known):
            onsite = app.plex_link_config('10.44.10.55', '10.44.10.30')
            self.assertEqual(onsite, {'mode': 'local', 'base': 'http://10.44.10.30:32400/web/index.html'})
            other_lan = app.plex_link_config('192.168.77.11', '10.44.10.30')
            self.assertEqual(other_lan['mode'], 'local')
            loop = app.plex_link_config('127.0.0.1', '127.0.0.1')
            self.assertEqual(loop['base'], 'http://127.0.0.1:32400/web/index.html')
            self.assertEqual(app.plex_link_config('203.0.113.11', '10.44.10.30'),
                             {'mode':'remote','base':'https://app.plex.tv/desktop/'})
            self.assertEqual(app.plex_link_config('10.10.20.45', '10.44.10.30')['mode'], 'remote')

    @patch.object(app, 'provider_enabled', new=lambda name: name == 'tmdb')
    def test_artwork_search_uses_tmdb_first_when_portrait_found(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        def fake_get(url, bearer=None):
            if 'themoviedb' in url:
                return {'results': [
                    {'id': 12, 'name': 'Sample Actor', 'profile_path': '/portrait.jpg'},
                    {'id': 13, 'name': 'Sample Actor Jr', 'profile_path': '/wrong.jpg'},
                ]}
            if 'theporndb' in url:
                return {'data': [{'id': 'z1', 'name': 'Sample Actor', 'image': 'https://cdn.theporndb.net/abc.jpg'}]}
            if 'wbsearchentities' in url:
                return {'search': [{'id': 'Q24', 'label': 'Sample Actor'}]}
            if 'wbgetentities' in url:
                return {'entities': {'Q24': {'claims': {'P18': [{'mainsnak': {'datavalue': {'value': 'Test portrait.jpg'}}}]}}}}
            raise AssertionError(url)
        with patch.object(app, 'artwork_keys', return_value={'tmdb':'secret','theporndb':'secret'}), \
                patch.object(app, 'provider_json', side_effect=fake_get):
            data = app.find_art('sample actor')
        self.assertEqual([x['source'] for x in data['results']], ['TMDB'])
        self.assertNotIn('Sample Actor Jr', [x['name'] for x in data['results']])
        self.assertTrue(all(x['preview'].startswith('/api/art/preview?id=') for x in data['results']))

    @patch.object(app, 'provider_enabled', new=lambda name: name == 'tmdb')
    def test_artwork_search_falls_back_to_tpdb_without_tmdb_portrait(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        calls = []
        def fake_get(url, bearer=None):
            calls.append(url)
            if 'themoviedb.org' in url:
                return {'results': [{'id': 12, 'name': 'Sample Actor', 'profile_path': None}]}
            if 'theporndb.net' in url:
                return {'data': [{'id': 'z1', 'name': 'Sample Actor', 'image': 'https://cdn.theporndb.net/abc.jpg'}]}
            raise AssertionError(url)
        with patch.object(app, 'artwork_keys', return_value={'tmdb': 't', 'theporndb': 'p'}), \
             patch.object(app, 'provider_json', side_effect=fake_get):
            result = app.find_art('sample actor')
        self.assertEqual([x['source'] for x in result['results']], ['ThePornDB'])
        self.assertEqual(len(calls), 2)
        self.assertIn('themoviedb.org', calls[0])
        self.assertIn('theporndb.net', calls[1])

    def test_artwork_override_survives_reindex_and_reverts(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        choice = app.new_art_candidate('sample actor', 'Sample Actor', 'https://image.tmdb.org/t/p/w185/portrait.jpg',
                                      'TMDB', 'https://www.themoviedb.org/person/12', 'TMDB')
        with patch.object(app, 'external_image', return_value=(b'\xff\xd8\xff' + b'image', 'jpg')):
            app.apply_art('sample actor', choice['id'])
        self.assertEqual(app.image_bytes('actor', 'sample actor'), b'\xff\xd8\xffimage')
        self.assertEqual(app.get_actor('sample actor')['art']['source'], 'TMDB')
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        self.assertEqual(app.get_actor('sample actor')['art']['source'], 'TMDB')
        app.remove_art('sample actor')
        self.assertEqual(app.get_actor('sample actor')['art']['source'], 'Plex')

    def test_artwork_choice_cannot_be_applied_to_another_person(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        choice = app.new_art_candidate('sample actor', 'Sample Actor', 'https://image.tmdb.org/t/p/w185/portrait.jpg',
                                      'TMDB', 'https://www.themoviedb.org/person/12', 'TMDB')
        with self.assertRaisesRegex(ValueError, 'does not belong'):
            app.apply_art('second actor', choice['id'])

    def test_image_redirect_restrictions(self):
        for url in ('http://image.tmdb.org/foo.jpg', 'https://127.0.0.1/photo.jpg',
                    'https://localhost/img.jpg', 'file:///etc/passwd'):
            with self.assertRaises(ValueError):
                app.external_image(url)


    def test_credit_matching_uses_titles_types_and_years(self):
        local = [
            {'title':'The Signal!', 'year':2019, 'media_type':'movie'},
            {'title':'Northern Lights', 'year':2022, 'media_type':'show'},
            {'title':'Crash Course', 'year':2020, 'media_type':'movie'},
        ]
        external = [
            {'title':'The Signal', 'release_date':'2019-02-02', 'media_type':'movie'},
            {'name':'Northern Lights', 'first_air_date':'2022-05-01', 'media_type':'tv'},
            {'title':'Crash', 'release_date':'2020-03-01', 'media_type':'movie'},
            {'title':'The Signal', 'release_date':'2014-02-02', 'media_type':'movie'},
        ]
        matches = app.credit_matches(local, external, 'TMDB')
        self.assertEqual([x['title'] for x in matches], ['The Signal!', 'Northern Lights'])
        self.assertTrue(all(x['year_verified'] for x in matches))

    def test_singleton_requires_title_name_no_conflict_and_complete_provider(self):
        evidence = [{'title':'Movie One','year':2018,'external_year':2018,'year_verified':True}]
        good = {'name':'Ada Example','source':'TMDB','url':'https://image.tmdb.org/t/p/w342/ada.jpg',
                'matches':evidence}
        self.assertEqual(app.choose_automatic_candidate([good], actor_name='Ada Example'), good)
        self.assertIsNone(app.choose_automatic_candidate([good], actor_name='Other Person'))
        self.assertIsNone(app.choose_automatic_candidate([good], actor_name='Ada Example', errors=['TPDB timed out']))
        self.assertIsNone(app.choose_automatic_candidate([dict(good, matches=[])], actor_name='Ada Example'))
        self.assertIs(app.choose_automatic_candidate([dict(good, matches=[dict(evidence[0], role_conflict=True)])], actor_name='Ada Example')['source'], good['source'])
        self.assertIsNone(app.choose_automatic_candidate([dict(good, matches=[dict(evidence[0], external_year=2020)])], actor_name='Ada Example'))
        self.assertIsNone(app.choose_automatic_candidate([dict(good, url='http://127.0.0.1/p.jpg')], actor_name='Ada Example'))
        self.assertIsNone(app.choose_automatic_candidate([good, dict(good, source='ThePornDB')], actor_name='Ada Example'))

    def test_multiple_candidates_require_strong_evidence_and_unique_winner(self):
        evidence = [{'title':'Movie One','year':2018,'year_verified':True},
                    {'title':'Movie Two','year':2020,'year_verified':False}]
        good = {'name':'Ada Example','source':'TMDB', 'matches':evidence}
        weaker = dict(good, matches=evidence[:1])
        self.assertEqual(app.choose_automatic_candidate([good, weaker]), good)
        self.assertIsNone(app.choose_automatic_candidate([weaker, good]))
        self.assertIsNone(app.choose_automatic_candidate([good, dict(good, source='ThePornDB')]))

    def test_existing_review_queue_batch_accepts_only_verified_singletons(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        good = {'name':'Sample Actor','source':'ThePornDB','url':'https://cdn.theporndb.net/a.jpg',
                'reference':'https://theporndb.net/performers/12',
                'matches':[{'title':'Alpha','year':2024,'external_year':2024,'year_verified':True}]}
        bad = dict(good, name='Different Person')
        app.remember_enrichment('sample actor', 'review', [good])
        app.remember_enrichment('second actor', 'review', [bad])
        with patch.object(app, 'external_image', return_value=(b'\xff\xd8\xff' + b'fake','jpg')):
            app.review_single_batch_worker()
        self.assertEqual(app.get_actor('sample actor')['art']['source'], 'ThePornDB')
        self.assertFalse(app.get_actor('second actor')['art']['source'])
        self.assertEqual(app.enrichment_status()['review_waiting'], 1)
        self.assertEqual(app.enrichment_status()['single_batch']['applied'], 1)

    def test_batch_retain_incomplete_provider_results(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        good = {'name':'Sample Actor','source':'TMDB','url':'https://image.tmdb.org/t/p/w342/a.jpg',
                'matches':[{'title':'Alpha','year':2024,'external_year':2024,'year_verified':True}]}
        app.remember_enrichment('sample actor', 'review', [good], 'TMDB credits: timeout')
        with patch.object(app, 'external_image') as img:
            app.review_single_batch_worker()
            img.assert_not_called()
        self.assertEqual(app.enrichment_status()['single_batch']['skipped'], 1)
        self.assertEqual(app.enrichment_status()['review_waiting'], 1)

    @patch.object(app, 'provider_enabled', new=lambda name: name in ('tmdb', 'wikimedia'))
    def test_provider_verification_uses_both_movie_and_tv_credits(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        def fake_provider(url, token):
            if '/search/person' in url:
                return {'results':[{'id':24,'name':'Sample Actor','profile_path':'/ok.jpg'},
                                   {'id':25,'name':'Sample Actor Other','profile_path':'/wrong.jpg'}]}
            if '/person/24/combined_credits' in url:
                return {'cast':[{'title':'Alpha','media_type':'movie','release_date':'2024-06-11'},
                                {'name':'Series 1','media_type':'tv','first_air_date':'2022-11-01'}]}
            raise AssertionError(url)
        with patch.object(app, 'artwork_keys', return_value={'tmdb':'token','theporndb':''}), \
                patch.object(app, 'paced_provider_json', side_effect=fake_provider):
            matches, errors = app.verified_portrait_candidates('sample actor')
        self.assertEqual(errors, [])
        self.assertEqual(len(matches), 1)
        self.assertEqual(len(matches[0]['matches']), 2)
        self.assertTrue(app.is_strong_match(matches[0]))

    def test_imdb_known_for_breaks_tied_tmdb_identity_candidates(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        first = {'name': 'Sample Actor', 'source': 'TMDB',
                 'url': 'https://image.tmdb.org/t/p/w342/a.jpg',
                 'reference': 'https://www.themoviedb.org/person/10',
                 'matches': [{'title': 'Alpha', 'year': 2024,
                              'external_year': 2024, 'year_verified': True}]}
        second = dict(first, reference='https://www.themoviedb.org/person/20',
                      url='https://image.tmdb.org/t/p/w342/b.jpg')
        def external(url, token):
            return {'imdb_id': 'nm111' if '/10/' in url else 'nm222'}
        with patch.object(app, 'IMDB_INDEX_PATH', Path(self.temp.name)), \
             patch.object(app, 'paced_provider_json', side_effect=external), \
             patch.object(app.imdb_identity, 'supporting_credits',
                          side_effect=lambda path, ident, local: 1 if ident == 'nm222' else 0):
            winner = app.imdb_resolve_candidates([first, second], 'sample actor')
        self.assertEqual(winner['reference'], second['reference'])

    def test_imdb_unknown_does_not_resolve_competing_identities(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        first = {'name': 'Sample Actor', 'source': 'TMDB',
                 'url': 'https://image.tmdb.org/t/p/w342/a.jpg',
                 'reference': 'https://www.themoviedb.org/person/10',
                 'matches': [{'title': 'Alpha', 'year': 2024,
                              'external_year': 2024, 'year_verified': True}]}
        second = dict(first, url='https://image.tmdb.org/t/p/w342/b.jpg',
                      reference='https://www.themoviedb.org/person/20')
        with patch.object(app, 'IMDB_INDEX_PATH', Path(self.temp.name)), \
             patch.object(app, 'paced_provider_json', return_value={'imdb_id': 'nm111'}), \
             patch.object(app.imdb_identity, 'supporting_credits', return_value=0):
            self.assertIsNone(app.imdb_resolve_candidates([first, second], 'sample actor'))

    def test_duplicate_tmdb_portraits_keep_only_one_candidate_without_merging_credits(self):
        first = {'name':'Troy Brown','source':'TMDB',
                 'url':'https://image.tmdb.org/t/p/w342/same.jpg',
                 'reference':'https://www.themoviedb.org/person/10',
                 'matches':[{'title':'2 Fast 2 Furious','year':2003,'external_year':2003,
                             'year_verified':True}]}
        second = {'name':'Troy Brown','source':'TMDB',
                  'url':'https://image.tmdb.org/t/p/w342/same.jpg',
                  'reference':'https://www.themoviedb.org/person/20',
                  'matches':[{'title':'Twisted Metal','year':2023,'external_year':2023,
                              'year_verified':True}]}
        collapsed = app.deduplicate_portrait_candidates([first, second])
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(len(collapsed[0]['matches']), 1)
        self.assertFalse(app.is_strong_match(collapsed[0]))
        self.assertEqual(len(app.deduplicate_portrait_candidates(
            [first, dict(second, url='https://image.tmdb.org/t/p/w342/other.jpg')])), 2)

    def test_saved_review_duplicates_are_consolidated_before_batch(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        candidate = {'name':'Second Actor','source':'TMDB',
                     'url':'https://image.tmdb.org/t/p/w342/same.jpg',
                     'reference':'https://www.themoviedb.org/person/10',
                     'matches':[{'title':'Alpha','year':2024,'external_year':2024,
                                 'year_verified':True}]}
        with app.db_open() as db:
            db.execute('INSERT INTO enrichment_results(actor_key,status,candidates,checked_at,message) VALUES(?,?,?,?,?)',
                       ('second actor','review',json.dumps([candidate,dict(candidate,reference='https://www.themoviedb.org/person/20')]),'',''))
        self.assertEqual(app.deduplicate_saved_reviews(), 1)
        self.assertEqual(len(app.review_enrichment()[0]['choices']), 1)
        self.assertEqual(app.deduplicate_saved_reviews(), 0)

    def test_review_queue_is_persistent_and_requires_selection(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        choice = {'name':'Second Actor','source':'ThePornDB','url':'https://cdn.theporndb.net/x.jpg',
                  'reference':'https://theporndb.net/performers/123',
                  'credit':'ThePornDB','matches':[{'title':'Alpha','year':2024,'year_verified':True}]}
        app.remember_enrichment('second actor', 'review', [choice])
        reviews = app.review_enrichment()
        self.assertEqual(len(reviews),1)
        self.assertEqual(reviews[0]['choices'][0]['matches'][0]['title'],'Alpha')
        with self.assertRaisesRegex(ValueError, 'Unknown artwork'):
            app.approve_enrichment('second actor', 4)
        with patch.object(app, 'external_image', return_value=(b'\xff\xd8\xff' + b'fake', 'jpg')):
            app.approve_enrichment('second actor',0)
        self.assertEqual(app.get_actor('second actor')['art']['source'], 'ThePornDB')
        self.assertEqual(app.enrichment_status()['review_waiting'], 0)
        self.assertEqual(app.image_bytes('actor','second actor'),b'\xff\xd8\xfffake')

    def test_review_includes_plex_title_context_and_character(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        evidence = {'name':'Sample Actor','source':'TMDB',
                    'url':'https://image.tmdb.org/t/p/w342/x.jpg',
                    'reference':'https://www.themoviedb.org/person/6',
                    'matches':[{'title':'Alpha','year':2024,'external_year':2024,'year_verified':True}]}
        app.remember_enrichment('sample actor','review',[evidence])
        entry=app.review_enrichment()[0]
        self.assertEqual(entry['plex_title_count'],3)
        self.assertEqual({x['library'] for x in entry['plex_titles']},{'Movies','Series'})
        self.assertIn('Detective',[x['character'] for x in entry['plex_titles']])
        self.assertEqual(entry['choices'][0]['preview'], '/api/enrich/preview?key=sample%20actor&i=0')

    def test_reject_one_candidate_preserves_other_candidates(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        candidates = [
            {'name':'Second Actor','source':'TMDB','url':'https://image.tmdb.org/t/p/w342/one.jpg','matches':[]},
            {'name':'Second Actor','source':'ThePornDB','url':'https://cdn.theporndb.net/two.jpg','matches':[]},
        ]
        app.remember_enrichment('second actor','review',candidates)
        with self.assertRaisesRegex(ValueError,'Unknown artwork'):
            app.reject_enrichment_candidate('second actor',2)
        self.assertTrue(app.reject_enrichment_candidate('second actor',0))
        remaining=app.review_enrichment()
        self.assertEqual(len(remaining),1)
        self.assertEqual(remaining[0]['choices'][0]['source'],'ThePornDB')
        self.assertFalse(app.reject_enrichment_candidate('second actor',0))
        self.assertEqual(app.enrichment_status()['review_waiting'],0)
        self.assertIsNone(app.get_actor('second actor')['art']['source'] or None)

    def test_existing_tmdb_review_can_display_full_resolution_preview(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        app.remember_enrichment('second actor','review',[{
            'source':'TMDB', 'url':'https://image.tmdb.org/t/p/w342/a.jpg',
            'name':'Second Actor','matches':[]}])
        with patch.object(app, 'external_image', return_value=(b'img', 'jpg')) as image:
            self.assertEqual(app.get_enrichment_preview('second actor', 0), (b'img', 'jpg'))
            image.assert_called_once_with('https://image.tmdb.org/t/p/h632/a.jpg')
        self.assertEqual(app.enrichment_status()['review_waiting'], 1)

    def test_conflicting_character_roles_block_automatic_application(self):
        local=[{'title':'Movie One','year':2019,'media_type':'movie','character':'Detective'},
               {'title':'Movie Two','year':2018,'media_type':'movie','character':'Agent'}]
        remote=[{'title':'Movie One','release_date':'2019-04-01','media_type':'movie','character':'Director'},
                {'title':'Movie Two','release_date':'2018-04-01','media_type':'movie','character':'Agent'}]
        matches=app.credit_matches(local,remote,'TMDB')
        self.assertTrue(matches[0]['role_conflict'])
        self.assertFalse(matches[1]['role_conflict'])
        self.assertTrue(app.is_strong_match({'matches':matches}))
        self.assertEqual(app.provider_other_credits(local,remote),[])
        self.assertEqual(app.provider_other_credits(local, remote+[{'title':'Different Project','year':2020}]),
                         [{'title':'Different Project','year':2020}])

    @patch.object(app, 'provider_enabled', new=lambda name: name in ('tmdb', 'wikimedia'))
    def test_unmatched_is_not_automatically_assigned(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        with patch.object(app, 'artwork_keys', return_value={'tmdb':'token','theporndb':''}), \
                patch.object(app, 'paced_provider_json', return_value={'results':[{
                    'id':33,'name':'Second Actor','profile_path':'/person.jpg'}]} ) as provider:
            # The person-search result exists, but no filmography match is available.
            matches, errors = app.verified_portrait_candidates('second actor')
        self.assertEqual(matches, [])
        self.assertEqual(errors, [])
        self.assertEqual(provider.call_count, 2)

    def test_tmdb_enabled_scans_plex_portraits_without_touching_saved_art(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        with patch.object(app, 'artwork_keys', return_value={'tmdb': 'key', 'theporndb': ''}), \
             patch.object(app, 'provider_enabled', return_value=True):
            self.assertIn('sample actor', app.pending_enrichment_keys())
            candidate = {'name': 'Sample Actor', 'source': 'TMDB',
                         'url': 'https://image.tmdb.org/t/p/w342/example.jpg',
                         'reference': 'https://www.themoviedb.org/person/1',
                         'credit': 'TMDB',
                         'matches': [{'title': 'Alpha', 'year': 2024, 'external_year': 2024,
                                      'year_verified': True},
                                     {'title': 'Beta', 'year': 2018, 'external_year': 2018,
                                      'year_verified': True}]}
            with patch.object(app, 'verified_portrait_candidates', return_value=([candidate], [])), \
                 patch.object(app, 'external_image', return_value=(b'\\xff\\xd8\\xffTMDB', 'jpg')):
                app.ENRICH_STOP.clear()
                app.enrichment_worker()
            self.assertEqual(app.get_actor('sample actor')['art']['source'], 'TMDB')
            self.assertEqual(app.image_bytes('actor', 'sample actor'), b'\\xff\\xd8\\xffTMDB')
            self.assertNotIn('sample actor', app.pending_enrichment_keys())

    def test_tmdb_replaces_saved_non_tmdb_art_and_blocks_tpdb_fallback(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        prior = app.new_art_candidate(
            'sample actor', 'Sample Actor', 'https://cdn.theporndb.net/old.jpg',
            'ThePornDB', 'https://theporndb.net/performers/1', 'ThePornDB')
        with patch.object(app, 'external_image', return_value=(b'\\xff\\xd8\\xffold', 'jpg')):
            app.apply_art('sample actor', prior['id'])
        tmdb = {'name': 'Sample Actor', 'source': 'TMDB',
                'url': 'https://image.tmdb.org/t/p/w342/new.jpg',
                'reference': 'https://www.themoviedb.org/person/42',
                'credit': 'TMDB',
                'matches': [{'title': 'Alpha', 'year': 2024,
                             'external_year': 2024, 'year_verified': True},
                            {'title': 'Beta', 'year': 2018,
                             'external_year': 2018, 'year_verified': True}]}
        with patch.object(app, 'artwork_keys', return_value={'tmdb': 't', 'theporndb': 'p'}), \
             patch.object(app, 'provider_enabled', return_value=True):
            self.assertIn('sample actor', app.pending_enrichment_keys())
            with patch.object(app, 'verified_portrait_candidates', return_value=([tmdb], [])), \
                 patch.object(app, 'external_image', return_value=(b'\\xff\\xd8\\xffnew', 'jpg')):
                app.ENRICH_STOP.clear()
                app.enrichment_worker()
            self.assertEqual(app.get_actor('sample actor')['art']['source'], 'TMDB')
            self.assertEqual(app.image_bytes('actor', 'sample actor'), b'\\xff\\xd8\\xffnew')
            self.assertNotIn('sample actor', app.pending_enrichment_keys())

    @patch.object(app, 'provider_enabled', new=lambda name: name == 'tmdb')
    def test_existing_saved_art_kept_when_external_providers_have_no_match(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        prior = app.new_art_candidate(
            'second actor', 'Second Actor', 'https://cdn.theporndb.net/old.jpg',
            'ThePornDB', 'https://theporndb.net/performers/1', 'ThePornDB')
        with patch.object(app, 'external_image', return_value=(b'\\xff\\xd8\\xffold', 'jpg')):
            app.apply_art('second actor', prior['id'])
        with patch.object(app, 'artwork_keys', return_value={'tmdb': 't', 'theporndb': 'p'}), \
             patch.object(app, 'paced_provider_json', side_effect=[
                 {'results': []}, {'data': []}]) as provider:
            candidates, errors = app.verified_portrait_candidates('second actor')
        self.assertEqual((candidates, errors), ([], []))
        self.assertEqual(provider.call_count, 2)
        self.assertEqual(app.get_actor('second actor')['art']['source'], 'ThePornDB')

    def test_unique_two_credit_portrait_ignores_role_label_difference(self):
        entry = {'name': 'Verne Lundquist', 'source': 'TMDB',
                 'url': 'https://image.tmdb.org/t/p/w342/photo.jpg',
                 'matches': [
                     {'title': 'Happy Gilmore', 'year': 1996,
                      'external_year': 1996, 'year_verified': True,
                      'plex_character': 'Announcer', 'provider_character': 'Announcer'},
                     {'title': 'The Last Boy Scout', 'year': 1991,
                      'external_year': 1991, 'year_verified': True,
                      'plex_character': 'Himself', 'provider_character': 'Verne Lundquist',
                      'role_conflict': True},
                 ]}
        self.assertTrue(app.singleton_is_verified('Verne Lundquist', [entry]))
        self.assertTrue(app.confident_portrait_replacement('Verne Lundquist', [entry]))
        self.assertIsNone(app.choose_automatic_candidate([entry, entry], 'Verne Lundquist'))
        self.assertFalse(app.confident_portrait_replacement(
            'Verne Lundquist', [dict(entry, matches=[]) ]))

    def test_single_exact_year_credit_can_replace_existing_plex_portrait(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        choice = {'name': 'Sample Actor', 'source': 'TMDB',
                  'url': 'https://image.tmdb.org/t/p/w342/a.jpg',
                  'reference': 'https://www.themoviedb.org/person/1',
                  'credit': 'TMDB',
                  'matches': [{'title': 'Alpha', 'year': 2024,
                               'external_year': 2024, 'year_verified': True}]}
        with patch.object(app, 'pending_enrichment_keys', return_value=['sample actor']), \
             patch.object(app, 'verified_portrait_candidates', return_value=([choice], [])), \
             patch.object(app, 'external_image', return_value=(b'\\xff\\xd8\\xffnew', 'jpg')):
            app.ENRICH_STOP.clear()
            app.enrichment_worker()
        self.assertEqual(app.get_actor('sample actor')['art']['source'], 'TMDB')
        self.assertEqual(app.enrichment_status()['review_waiting'], 0)

    def test_one_credit_without_exact_year_cannot_replace_existing_art(self):
        match = {'title': 'Alpha', 'year': 2024,
                 'external_year': None, 'year_verified': False}
        choice = {'name': 'Sample Actor', 'source': 'TMDB',
                  'url': 'https://image.tmdb.org/t/p/w342/a.jpg',
                  'matches': [match]}
        self.assertFalse(app.confident_portrait_replacement('Sample Actor', [choice]))
        self.assertTrue(app.confident_portrait_replacement(
            'Sample Actor', [dict(choice, matches=[dict(match, external_year=2024,
                                                       year_verified=True, role_conflict=True)])]))
        self.assertFalse(app.confident_portrait_replacement('Sample Actor', [choice, choice]))

    def test_weak_tmdb_match_does_not_replace_existing_plex_portrait(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        candidate = {'name': 'Sample Actor', 'source': 'TMDB',
                     'url': 'https://image.tmdb.org/t/p/w342/ambiguous.jpg',
                     'reference': 'https://www.themoviedb.org/person/77',
                     'credit': 'TMDB',
                     'matches': [{'title': 'Alpha', 'year': 2024,
                                  'external_year': None, 'year_verified': False}]}
        with patch.object(app, 'pending_enrichment_keys', return_value=['sample actor']), \
             patch.object(app, 'verified_portrait_candidates', return_value=([candidate], [])), \
             patch.object(app, 'external_image') as image:
            app.ENRICH_STOP.clear()
            app.enrichment_worker()
            image.assert_not_called()
        self.assertEqual(app.get_actor('sample actor')['art']['source'], 'Plex')
        self.assertEqual(app.enrichment_status()['review_waiting'], 1)

    def test_tmdb_disabled_keeps_existing_plex_portrait_priority(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        with patch.object(app, 'artwork_keys', return_value={'tmdb': 'key', 'theporndb': 'key'}), \
             patch.object(app, 'provider_enabled', return_value=False):
            self.assertIn('sample actor', app.pending_enrichment_keys())
            self.assertIn('second actor', app.pending_enrichment_keys())

    def test_sync_wrapper_starts_enrichment_only_after_successful_sync(self):
        with patch.object(app, 'sync_all') as sync, \
             patch.object(app, 'status_snapshot', return_value={'phase': 'Finished'}), \
             patch.object(app, 'enrichment_start') as enrich:
            app.sync_and_enrich(force=True)
        sync.assert_called_once_with(force=True)
        enrich.assert_called_once()

    def test_diagnostic_export_summarizes_reviews_without_secrets(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        app.remember_enrichment('sample actor', 'review', [{
            'source': 'TMDB', 'name': 'Sample Actor',
            'url': 'https://example.org/portrait?token=private-value',
            'matches': [{'title': 'Alpha', 'year_verified': True}]}])
        snapshot = app.diagnostic_export()
        self.assertEqual(snapshot['counts']['actors_total'], 2)
        self.assertEqual(snapshot['counts']['review'], 1)
        self.assertEqual(snapshot['samples'][0]['candidates'][0]['matching_credits'], 1)
        self.assertNotIn('private-value', json.dumps(snapshot))
        self.assertNotIn('example.org', json.dumps(snapshot))

    def test_completed_enrichment_results_are_not_requeued(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        self.assertIn('sample actor', app.pending_enrichment_keys())
        app.remember_enrichment('sample actor', 'auto')
        app.remember_enrichment('second actor', 'unmatched')
        self.assertEqual(app.pending_enrichment_keys(), [])
        self.assertEqual(app.enrichment_status()['remaining'], 0)

    @patch.object(app, 'provider_enabled', new=lambda name: name == 'tmdb')
    def test_tpdb_is_considered_before_existing_plex_fallback(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        def provider(url, token):
            if '/search/person?' in url:
                return {'results': []}
            if '/performers?' in url:
                return {'data': [{'_id': 'p9', 'name': 'Sample Actor',
                                  'image': 'https://cdn.theporndb.net/a.jpg'}]}
            if '/performers/p9/scenes?' in url:
                return {'data': [{'title': 'Alpha', 'year': 2024}]}
            raise AssertionError(url)
        with patch.object(app, 'artwork_keys', return_value={'tmdb': 't', 'theporndb': 'p'}), \
             patch.object(app, 'paced_provider_json', side_effect=provider):
            choices, errors = app.verified_portrait_candidates('sample actor')
        self.assertEqual(errors, [])
        self.assertEqual([choice['source'] for choice in choices], ['ThePornDB'])

    def test_background_enrichment_auto_applies_and_resumes(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        candidate = {'name':'Second Actor','source':'ThePornDB',
                     'url':'https://cdn.theporndb.net/x.jpg',
                     'reference':'https://theporndb.net/performers/2',
                     'credit':'ThePornDB',
                     'matches':[{'title':'Alpha','year':2024,'year_verified':True},
                                {'title':'Beta','year':2018,'year_verified':False}]}
        with patch.object(app, 'pending_enrichment_keys', return_value=['second actor']), \
             patch.object(app, 'verified_portrait_candidates', return_value=([candidate],[])), \
             patch.object(app, 'external_image', return_value=(b'\xff\xd8\xffauto','jpg')):
            app.ENRICH_STOP.clear()
            app.enrichment_worker()
        self.assertEqual(app.get_actor('second actor')['art']['source'],'ThePornDB')
        self.assertEqual(app.enrichment_status()['db_auto'],1)
        self.assertEqual(app.enrichment_status()['review_waiting'],0)
        self.assertEqual(app.pending_enrichment_keys(), ['sample actor'])

    def test_background_enrichment_defers_ambiguous_matches(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        evidence = [{'title':'Alpha','year':2024,'year_verified':True},
                    {'title':'Beta','year':2018,'year_verified':True}]
        candidates = [{'name':'Second Actor','source':'TMDB','url':'https://image.tmdb.org/t/p/w342/x.jpg',
                       'reference':'https://www.themoviedb.org/person/20','credit':'TMDB','matches':evidence},
                      {'name':'Second Actor','source':'ThePornDB','url':'https://cdn.theporndb.net/y.jpg',
                       'reference':'https://theporndb.net/performers/11','credit':'ThePornDB','matches':evidence}]
        with patch.object(app, 'pending_enrichment_keys', return_value=['second actor']), \
             patch.object(app, 'verified_portrait_candidates', return_value=(candidates,[])):
            app.ENRICH_STOP.clear()
            app.enrichment_worker()
        self.assertEqual(app.enrichment_status()['review_waiting'],1)
        self.assertFalse(app.get_actor('second actor')['art']['source'])
        self.assertEqual(len(app.review_enrichment()[0]['choices']),2)

    def test_retry_unmatched_does_not_erase_review_or_applied_portraits(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        app.remember_enrichment('second actor', 'unmatched')
        app.remember_enrichment('sample actor', 'review', [], '')
        self.assertEqual(app.retry_unmatched_enrichment(), 1)
        self.assertEqual(len(app.review_enrichment()), 1)
        self.assertIn('second actor', app.pending_enrichment_keys())
        self.assertEqual(app.retry_unmatched_enrichment(), 0)

    @patch.object(app, 'provider_enabled', new=lambda name: name == 'tmdb')
    def test_verified_candidates_use_tmdb_without_calling_tpdb(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        calls = []
        def fake_provider(url, token):
            calls.append(url)
            if '/search/person?' in url:
                return {'results': [{'id': 24, 'name': 'Sample Actor', 'profile_path': '/ok.jpg'}]}
            if '/person/24/combined_credits' in url:
                return {'cast': [{'title': 'Alpha', 'media_type': 'movie', 'release_date': '2024-06-11'}]}
            raise AssertionError('TPDB should not be queried: '+url)
        with patch.object(app, 'artwork_keys', return_value={'tmdb': 'tmdb-key', 'theporndb': 'tpdb-key'}), \
             patch.object(app, 'paced_provider_json', side_effect=fake_provider):
            candidates, errors = app.verified_portrait_candidates('sample actor')
        self.assertEqual(errors, [])
        self.assertEqual([c['source'] for c in candidates], ['TMDB'])
        self.assertEqual(len(calls), 2)

    @patch.object(app, 'provider_enabled', new=lambda name: name == 'tmdb')
    def test_existing_plex_fallback_remains_when_tpdb_has_no_match(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        with patch.object(app, 'artwork_keys', return_value={'tmdb': 't', 'theporndb': 'p'}), \
             patch.object(app, 'provider_enabled', return_value=True), \
             patch.object(app, 'paced_provider_json',
                          side_effect=[{'results': []}, {'data': []}]) as provider:
            candidates, errors = app.verified_portrait_candidates('sample actor')
        self.assertEqual((candidates, errors), ([], []))
        self.assertEqual(provider.call_count, 2)
        self.assertEqual(app.get_actor('sample actor')['art']['source'], 'Plex')

    @patch.object(app, 'provider_enabled', new=lambda name: name == 'tmdb')
    def test_verified_candidates_fall_back_to_tpdb_if_tmdb_lacks_portrait(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        requested = []
        def fake_provider(url, token):
            requested.append(url)
            if '/search/person?' in url:
                return {'results': [{'id': 24, 'name': 'Second Actor', 'profile_path': None}]}
            if '/performers?' in url:
                return {'data': [{'_id': 'p123', 'name': 'Second Actor',
                                  'image': 'https://cdn.theporndb.net/p.jpg'}]}
            if '/performers/p123/scenes?' in url:
                return {'data': [{'title': 'Alpha', 'year': 2024}]}
            raise AssertionError('Unexpected request: '+url)
        with patch.object(app, 'artwork_keys', return_value={'tmdb': 'tmdb-key',
                                                              'theporndb': 'tpdb-key'}), \
             patch.object(app, 'paced_provider_json', side_effect=fake_provider):
            candidates, errors = app.verified_portrait_candidates('second actor')
        self.assertEqual(errors, [])
        self.assertEqual([x['source'] for x in candidates], ['ThePornDB'])
        self.assertEqual(len(requested), 3)
        self.assertIn('themoviedb.org', requested[0])
        self.assertIn('theporndb.net', requested[1])
        self.assertIn('/scenes?', requested[2])

    def test_retry_failed_lookups_only(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        app.remember_enrichment('second actor','error',[], 'Provider 429')
        app.remember_enrichment('sample actor','review',[], '')
        self.assertEqual(app.retry_enrichment_errors(), 1)
        self.assertEqual(len(app.review_enrichment()), 1)



if __name__ == '__main__':
    unittest.main()
