"""Security regression tests for trusted external portrait retrieval."""
import unittest
from urllib.request import Request

import app


class ExternalArtworkSecurityTests(unittest.TestCase):
    def test_approved_url_requires_https_trusted_host_and_standard_port(self):
        approved = 'https://metadata-static.plex.tv/person/portrait.jpg'
        self.assertTrue(app.allowed_https_image_url(approved, app.ALLOWED_REMOTE_IMAGES))
        for unsafe in (
            'http://metadata-static.plex.tv/person/portrait.jpg',
            'https://metadata-static.plex.tv:8443/portrait.jpg',
            'https://user:pass@metadata-static.plex.tv/portrait.jpg',
            'https://metadata-static.plex.tv.evil.example/portrait.jpg',
            'https://127.0.0.1/portrait.jpg',
            'https://metadata-static.plex.tv:invalid/portrait.jpg',
            'file:///etc/passwd',
        ):
            with self.subTest(unsafe=unsafe):
                self.assertFalse(app.allowed_https_image_url(unsafe, app.ALLOWED_REMOTE_IMAGES))

    def test_plex_portrait_redirects_cannot_escape_plex_image_host_allowlist(self):
        handler = app.ArtworkRedirects(app.ALLOWED_REMOTE_IMAGES)
        req = Request('https://metadata-static.plex.tv/person/portrait.jpg')
        for unsafe in (
            'http://metadata-static.plex.tv/person/portrait.jpg',
            'https://metadata-static.plex.tv:8080/person/portrait.jpg',
            'https://user@metadata-static.plex.tv/person/portrait.jpg',
            'https://cdn.theporndb.net/portrait.jpg',
            'https://127.0.0.1/metadata',
            'https://metadata-static.plex.tv.evil.example/portrait.jpg',
        ):
            with self.subTest(unsafe=unsafe):
                with self.assertRaises(ValueError):
                    handler.redirect_request(req, None, 302, 'Found', {}, unsafe)
        valid = handler.redirect_request(req, None, 302, 'Found', {},
                                         'https://assets.plex.tv/portrait.jpg')
        self.assertEqual(valid.full_url, 'https://assets.plex.tv/portrait.jpg')

    def test_external_provider_redirects_reject_untrusted_ports_and_credentials(self):
        handler = app.ArtworkRedirects()
        req = Request('https://image.tmdb.org/t/p/w342/a.jpg')
        with self.assertRaises(ValueError):
            handler.redirect_request(req, None, 302, 'Found', {},
                                     'https://image.tmdb.org:9000/t/p/w342/a.jpg')
        with self.assertRaises(ValueError):
            handler.redirect_request(req, None, 302, 'Found', {},
                                     'https://alice@image.tmdb.org/t/p/w342/a.jpg')
        follow = handler.redirect_request(req, None, 302, 'Found', {},
                                          'https://upload.wikimedia.org/example.jpg')
        self.assertEqual(follow.full_url, 'https://upload.wikimedia.org/example.jpg')


if __name__ == '__main__':
    unittest.main()
