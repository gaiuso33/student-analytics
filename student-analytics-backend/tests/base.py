import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

ADMIN = ("admin", "test-admin-password")
VIEWER = ("viewer1", "viewer-password-1")


class ApiTestCase(unittest.TestCase):
    config = {}

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.app = create_app({
            "DATABASE": os.path.join(cls.tmp.name, "test.db"),
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "ADMIN_USERNAME": ADMIN[0],
            "ADMIN_PASSWORD": ADMIN[1],
            **cls.config,
        })
        cls.client = cls.app.test_client()
        cls.admin_token = cls.login(*ADMIN)
        cls.create_user(*VIEWER, role="viewer")
        cls.viewer_token = cls.login(*VIEWER)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def login(cls, username, password):
        res = cls.client.post("/api/auth/login", json={"username": username, "password": password})
        assert res.status_code == 200, res.get_data(as_text=True)
        return res.get_json()["token"]

    @classmethod
    def create_user(cls, username, password, role="viewer"):
        res = cls.client.post(
            "/api/users", json={"username": username, "password": password, "role": role},
            headers=cls.auth(cls.admin_token),
        )
        assert res.status_code == 201, res.get_data(as_text=True)

    @staticmethod
    def auth(token):
        return {"Authorization": f"Bearer {token}"}

    # convenience: authenticated requests (admin by default)
    def request(self, method, url, token=None, **kw):
        token = token or self.admin_token
        return self.client.open(url, method=method, headers=self.auth(token), **kw)

    def get(self, url, token=None):
        res = self.request("GET", url, token)
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        return res.get_json()
