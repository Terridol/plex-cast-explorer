"""Run with: python -m unittest test_app.py -v"""
import tempfile
import io
import json
import os
import ipaddress
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
import app


class PlexCastExplorerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db = app.DB_PATH
        self.old_conf = app.CONFIG_PATH
        self.old_portraits = app.PORTRAIT_DIR
        self.old_art_config = app.ART_CONFIG_PATH
        self.old_network_config = app.NETWORK_CONFIG_PATH
        app.DB_PATH = Path(self.temp.name) / 'data.sqlite'
        app.CONFIG_PATH = Path(self.temp.name) / 'settings.json'
        app.PORTRAIT_DIR = Path(self.temp.name) / 'portraits'
        app.ART_CONFIG_PATH = Path(self.temp.name) / 'artwork.json'
        app.NETWORK_CONFIG_PATH = Path(self.temp.name) / 'network.json'
        app.image_bytes.cache_clear()
        app.init_db()

    def tearDown(self):
        app.DB_PATH = self.old_db
        app.CONFIG_PATH = self.old_conf
        app.PORTRAIT_DIR = self.old_portraits
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
        self.assertIsNone(app.choose_automatic_candidate([dict(good, matches=[dict(evidence[0], role_conflict=True)])], actor_name='Ada Example'))
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
        self.assertFalse(app.is_strong_match({'matches':matches}))
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
        self.assertEqual(app.pending_enrichment_keys(),[])

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
    def test_verified_candidates_fall_back_to_tpdb_if_tmdb_lacks_portrait(self):
        with patch.object(app, 'plex_xml', side_effect=self.fake_xml):
            app.sync_all(force=True)
        requested = []
        def fake_provider(url, token):
            requested.append(url)
            if '/search/person?' in url:
                return {'results': [{'id': 24, 'name': 'Sample Actor', 'profile_path': None}]}
            if '/performers?' in url:
                return {'data': [{'_id': 'p123', 'name': 'Sample Actor',
                                  'image': 'https://cdn.theporndb.net/p.jpg'}]}
            if '/performers/p123/scenes?' in url:
                return {'data': [{'title': 'Alpha', 'year': 2024}]}
            raise AssertionError('Unexpected request: '+url)
        with patch.object(app, 'artwork_keys', return_value={'tmdb': 'tmdb-key',
                                                              'theporndb': 'tpdb-key'}), \
             patch.object(app, 'paced_provider_json', side_effect=fake_provider):
            candidates, errors = app.verified_portrait_candidates('sample actor')
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
