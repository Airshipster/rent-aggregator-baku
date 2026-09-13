import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch

from src.source_client import SourceBlockedError
from src.source_parser import SourceParser, item_status
from server.collector_service import check_published_statuses


class ListingStatusTests(unittest.TestCase):
    now = datetime(2026, 9, 13, 13, tzinfo=timezone.utc)

    def test_real_closed(self):
        self.assertEqual(item_status({'id':'6451158','isExpiredManually':True,
            'expiresAt':'2026-09-11T16:28:40+04:00'}, self.now), 'closed')

    def test_real_expired_not_manually_closed(self):
        self.assertEqual(item_status({'id':'6113739','isExpiredManually':False,
            'expiresAt':'2026-06-07T23:24:19+04:00'}, self.now), 'expired')

    def test_real_active(self):
        self.assertEqual(item_status({'id':'6457498','isExpiredManually':False,
            'expiresAt':None}, self.now), 'active')

    def test_future_and_exact_expiry(self):
        node = {'id':'1','isExpiredManually':False,'expiresAt':'2026-09-14T00:00:00Z'}
        self.assertEqual(item_status(node, self.now), 'active')
        node['expiresAt'] = '2026-09-13T17:00:00+04:00'
        self.assertEqual(item_status(node, self.now), 'expired')

    def test_incomplete_response_is_not_removal(self):
        parser = SourceParser(Mock())
        for data in ({}, {'item':{}}, {'item':{'id':'1'}},
                     {'item':{'id':'2','isExpiredManually':False,'expiresAt':None}}):
            parser.client.graphql.return_value = data
            with self.subTest(data=data), self.assertRaises((KeyError, ValueError)):
                parser.check_exists('1')

    def test_explicit_null_is_unavailable(self):
        parser = SourceParser(Mock())
        parser.client.graphql.return_value = {'item':None}
        self.assertEqual(parser.check_status('1'), 'unavailable')

    def test_source_errors_propagate(self):
        parser = SourceParser(Mock())
        for error in (SourceBlockedError('403'), TimeoutError(), RuntimeError('GraphQL error')):
            parser.client.graphql.side_effect = error
            with self.assertRaises(type(error)):
                parser.check_exists('1')

    def test_detail_uses_same_status(self):
        parser = SourceParser(Mock())
        parser.client.base_url = 'https://bina.az'
        detail = parser._detail_from_node({'id':'6113739','isExpiredManually':False,
                                          'expiresAt':'2026-06-07T23:24:19+04:00'})
        self.assertTrue(detail.is_deleted)
        self.assertEqual(detail.raw_status, 'expired')

    def test_invalid_expiry_is_not_removal(self):
        for expiry in ('invalid', '2026-01-01T00:00:00'):
            with self.assertRaises(ValueError):
                item_status({'id':'1','isExpiredManually':False,'expiresAt':expiry},self.now)

    def test_published_check_only_spools_confirmed_inactive(self):
        for status in ('active', 'closed', 'expired', 'unavailable'):
            conn = MagicMock()
            conn.execute.return_value.fetchone.return_value = None
            conn.execute.return_value.fetchall.return_value = [
                {'id':'00000000-0000-0000-0000-000000000001','source':'source','source_listing_id':'6113739'}]
            parser = Mock()
            parser.client.base_url = 'https://bina.az'
            parser.check_status.return_value = status
            with patch('server.collector_service.connect') as connect, \
                 patch('server.collector_service.sleep_soft'), \
                 patch('server.collector_service.beat'), \
                 patch('server.collector_service.store_spool') as spool:
                connect.return_value.__enter__.return_value = conn
                check_published_statuses(parser)
                self.assertEqual(spool.call_count, int(status != 'active'))

    def test_published_check_does_not_remove_on_error(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        conn.execute.return_value.fetchall.return_value = [
            {'id':'00000000-0000-0000-0000-000000000001','source':'source','source_listing_id':'6113739'}]
        parser = Mock()
        parser.check_status.side_effect = TimeoutError()
        with patch('server.collector_service.connect') as connect, \
             patch('server.collector_service.sleep_soft'), \
             patch('server.collector_service.beat') as beat, \
             patch('server.collector_service.store_spool') as spool:
            connect.return_value.__enter__.return_value = conn
            check_published_statuses(parser)
            spool.assert_not_called()
            self.assertFalse(any(call.args[0] == 'removal-cursor' for call in beat.call_args_list))
