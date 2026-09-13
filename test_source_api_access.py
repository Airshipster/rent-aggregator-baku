import ast
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from src.source_client import SourceClient, SourceBlockedError


class SourceApiAccessTests(unittest.TestCase):
    def test_collectors_do_not_require_html(self):
        for name in ('src/collector.py', 'server/collector_service.py'):
            tree = ast.parse(Path(name).read_text(encoding='utf-8'))
            calls = [node.func.attr for node in ast.walk(tree)
                     if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
            self.assertNotIn('get_start_page', calls, name)

    @patch.dict(os.environ, {'SOURCE_START_URL': 'https://bina.az/kiraye'})
    def test_graphql_does_not_fetch_html(self):
        client = SourceClient()
        response = Mock(status_code=200, text='{"data":{"__typename":"Query"}}')
        response.json.return_value = {'data': {'__typename': 'Query'}}
        client.session.request = Mock(return_value=response)
        self.assertEqual(client.graphql('{ __typename }', {}), {'__typename': 'Query'})
        self.assertEqual(client.session.request.call_count, 1)
        self.assertEqual(client.session.request.call_args.args,
                         ('POST', 'https://bina.az/graphql'))

    @patch.dict(os.environ, {'SOURCE_START_URL': 'https://bina.az/kiraye'})
    def test_api_block_still_stops_without_retries(self):
        client = SourceClient()
        client.session.request = Mock(return_value=Mock(
            status_code=403, text='Sorry, you have been blocked'))
        with self.assertRaises(SourceBlockedError):
            client.graphql('{ __typename }', {})
        self.assertEqual(client.session.request.call_count, 1)


if __name__ == '__main__':
    unittest.main()
