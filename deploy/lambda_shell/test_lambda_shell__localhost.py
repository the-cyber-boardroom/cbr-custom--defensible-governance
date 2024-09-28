import pytest

from unittest import TestCase
from cbr_website_beta.utils.remote_shell.CBR__Remote_Shell import CBR__Remote_Shell


class test_lambda_shell__localhost(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.function_url = 'http://localhost:5116'
        cls.cbr_shell = CBR__Remote_Shell(target_server=cls.function_url)
        if not cls.cbr_shell._lambda_auth_key():
            pytest.skip("no CBR__Remote_Shell auth key found")

    def test_ping(self):
        assert self.cbr_shell.ping() == 'pong'

    def test_reset_flask_cache(self):
        self.cbr_shell.target_server = 'http://localhost:5116'

        def reset_flask_cache():
            from cbr_website_beta.cbr__fastapi.CBR__Fast_API import cbr_fast_api
            flask     = cbr_fast_api.cbr__flask()
            flask_app = flask.app()
            flask_app.jinja_env.cache.clear() # todo: add this as a fast_api endpoint (for admins)

            return 'cache cleared'

        self.cbr_shell.function__print(reset_flask_cache)