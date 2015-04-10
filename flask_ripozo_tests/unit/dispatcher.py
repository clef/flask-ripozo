from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from flask import Flask

from flask_ripozo.dispatcher import FlaskDispatcher

from ripozo.exceptions import RestException

import mock
import unittest


class TestFlaskDispatcher(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)

    def get_mock_adapter_class(self):
        response_adapter = mock.MagicMock()
        response_adapter.formatted_body = 'some body'
        response_adapter.extra_headers = {'Content-Type': 'fake'}
        response_adapter.status_code = 600
        adapter_class = mock.Mock(return_value=response_adapter)
        adapter_class.formats = ['duh']
        adapter_class.format_exception = mock.Mock(return_value=('error', 'fake', 500,))
        return adapter_class

    def test_register_route(self):
        d = FlaskDispatcher(self.app)
        def fake():
            pass
        endpoint = 'someendpoint'
        values = dict(endpoint=endpoint, endpoint_func=fake,
                      route='/myresource', methods=['GET'])
        d.register_route(**values)
        self.assertIn(endpoint, self.app.url_map._rules_by_endpoint)
        rule = self.app.url_map._rules_by_endpoint[endpoint][0]
        self.assertIn('GET', rule.methods)
        self.assertEqual(rule.rule, '/myresource')
        self.assertEqual(endpoint, rule.endpoint)

        # They won't actually be the same function since it gets wrapped.
        self.assertEqual(self.app.view_functions[endpoint].func_name, fake.func_name)

    def test_flask_dispatch_wrapper(self):
        """
        Tests the wrapper to ensure that it properly calls the
        apimethod
        """
        adapter_class = self.get_mock_adapter_class()
        def fake(*args, **kwargs):
            return mock.Mock()

        d = FlaskDispatcher(self.app)
        d.register_adapters(adapter_class)
        view_func = d.flask_dispatch_wrapper(fake)
        self.assertEqual(view_func.func_name, fake.func_name)

        with self.app.test_request_context('/myresource'):
            response = view_func()
            self.assertEqual(response.content_type, 'fake')
            self.assertEqual(response.status_code, 600)
            self.assertEqual(response.data, 'some body')

    def test_flask_dispatch_wrapper_fail_restexception(self):
        """
        Tests the response when their is a failure in
        dispatching a request. In particular when a RestException
        is raised.
        """
        adapter_class = self.get_mock_adapter_class()
        def fake(*args, **kwargs):
            raise RestException

        d = FlaskDispatcher(self.app)
        d.register_adapters(adapter_class)
        view_func = d.flask_dispatch_wrapper(fake)
        self.assertEqual(view_func.func_name, fake.func_name)

        with self.app.test_request_context('/myresource'):
            response = view_func()
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.data, 'error')
            self.assertEqual(response.content_type, 'fake')

    def test_flask_dispatch_wrapper_fail(self):
        """
        Tests the response when their is a failure in
        dispatching a request that is not a RestException
        """
        adapter_class = self.get_mock_adapter_class()
        def fake(*args, **kwargs):
            raise Exception

        d = FlaskDispatcher(self.app)
        d.register_adapters(adapter_class)
        view_func = d.flask_dispatch_wrapper(fake)
        self.assertEqual(view_func.func_name, fake.func_name)

        with self.app.test_request_context('/myresource'):
            self.assertRaises(Exception, view_func)