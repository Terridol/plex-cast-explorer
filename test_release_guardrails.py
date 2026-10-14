"""LAN host validation and metadata provider opt-in checks."""
import os
import threading
import unittest
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

    def test_provider_opt_in_is_explicit(self):
        with patch.dict(os.environ, {'CAST_EXPLORER_ENABLE_TMDB': '1',
                                     'CAST_EXPLORER_ENABLE_WIKIMEDIA': '1'}):
            self.assertTrue(app.provider_enabled('tmdb'))
            self.assertTrue(app.provider_enabled('wikimedia'))
        with patch.dict(os.environ, {'CAST_EXPLORER_ENABLE_TMDB': 'true'}):
            self.assertFalse(app.provider_enabled('tmdb'))

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


if __name__ == '__main__':
    unittest.main()
