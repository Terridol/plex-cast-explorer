"""Regression tests for opt-in remote administration and separate credentials."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import app


class RemoteAdminTests(unittest.TestCase):
    def test_cidr_is_default_deny(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(app.approved_admin_address('100.101.22.12'))
        with patch.dict(os.environ, {'CAST_EXPLORER_REMOTE_ADMIN_CIDRS': '100.101.22.12/32'}):
            self.assertTrue(app.approved_admin_address('100.101.22.12'))
            self.assertFalse(app.approved_admin_address('100.101.22.13'))
            self.assertFalse(app.approved_admin_address('192.168.1.12'))

    def test_distinct_passwords_and_remote_admin_role(self):
        with tempfile.TemporaryDirectory() as work:
            old_auth, old_admin, old_port = app.AUTH_PATH, app.ADMIN_AUTH_PATH, app.PORT
            app.AUTH_PATH = Path(work) / 'auth.json'
            app.ADMIN_AUTH_PATH = Path(work) / 'admin_auth.json'
            app.set_password('gallery-password-123456')
            app.set_admin_password('independent-admin-password-123456')
            self.assertFalse(app.verify_admin_password('gallery-password-123456'))
            self.assertFalse(app.verify_password('independent-admin-password-123456'))
            self.assertTrue(app.verify_admin_password('independent-admin-password-123456'))
            server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
            app.PORT = server.server_port
            t = threading.Thread(target=server.serve_forever, daemon=True)
            with patch.object(app.Handler, 'is_local', return_value=False), patch.object(app, 'approved_admin_address', return_value=True):
                t.start()
                try:
                    base = f'http://127.0.0.1:{server.server_port}'
                    def post(path, body, cookie=''):
                        req = Request(base + path, data=json.dumps(body).encode(), method='POST',
                                      headers={'Content-Type':'application/json', 'Cookie': cookie})
                        return urlopen(req, timeout=4)
                    gallery_resp = post('/api/login', {'password':'gallery-password-123456'})
                    gallery_cookie = gallery_resp.headers['Set-Cookie'].split(';',1)[0]
                    with self.assertRaises(HTTPError) as bad:
                        urlopen(Request(base+'/api/art/config', headers={'Cookie':gallery_cookie}),timeout=4)
                    self.assertEqual(bad.exception.code, 403)
                    with self.assertRaises(HTTPError) as bad:
                        post('/api/admin/login', {'password':'gallery-password-123456'}, gallery_cookie)
                    self.assertEqual(bad.exception.code,401)
                    admin_resp=post('/api/admin/login', {'password':'independent-admin-password-123456'}, gallery_cookie)
                    admin_cookie=admin_resp.headers['Set-Cookie'].split(';',1)[0]
                    with urlopen(Request(base+'/api/config', headers={'Cookie': gallery_cookie+'; '+admin_cookie}),timeout=4) as response:
                        self.assertTrue(json.load(response)['admin'])
                    with post('/api/admin/logout', {}, gallery_cookie+'; '+admin_cookie) as response:
                        self.assertIn('Max-Age=0', response.headers['Set-Cookie'])
                finally:
                    server.shutdown();server.server_close();t.join(timeout=4)
                    app.AUTH_PATH, app.ADMIN_AUTH_PATH, app.PORT = old_auth, old_admin, old_port

if __name__=='__main__':
    unittest.main()
