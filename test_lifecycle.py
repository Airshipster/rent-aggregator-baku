import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import Mock,patch
from server import worker
from server.system_status import incidents, render
from src.telegram_errors import TelegramAPIError


class LifecycleTests(unittest.TestCase):
    def task(self,age=72):
        return {'task_type':'mark_removed','chat_id':1,'telegram_message_id':2,'language':'ru',
                'parent_sent_at':datetime.now(timezone.utc)-timedelta(hours=age),
                'payload':{'listing_id':'6113739','image_urls':[]}}

    def test_old_channel_is_compacted_without_delete_attempt(self):
        with patch.object(worker,'TelegramClient') as factory:
            worker.send('channel',self.task())
            call=factory.return_value.call.call_args
            self.assertEqual(call.args[0],'editMessageText')
            self.assertIn('❌',call.args[1]['text'])
            self.assertTrue(call.args[1]['link_preview_options']['is_disabled'])

    def test_new_channel_is_deleted(self):
        with patch.object(worker,'TelegramClient') as factory:
            factory.return_value.call.return_value=True
            self.assertEqual(worker.send('channel',self.task(1)),{'message_id':2})
            self.assertEqual(factory.return_value.call.call_args.args[0],'deleteMessage')

    def test_delete_429_does_not_fall_through_to_edit(self):
        with patch.object(worker,'TelegramClient') as factory:
            factory.return_value.call.side_effect=TelegramAPIError({'error_code':429})
            with self.assertRaises(TelegramAPIError): worker.send('channel',self.task(1))
            self.assertEqual(factory.return_value.call.call_count,1)

    def test_private_edit_preserves_rich_body(self):
        with patch.object(worker,'TelegramClient') as factory, patch.object(worker,'format_private_rich',return_value=('<p>original</p>',[])):
            worker.send('private',self.task())
            call=factory.return_value.call.call_args
            self.assertEqual(call.args[0],'editMessageText')
            self.assertIn('original',call.args[1]['rich_message']['html'])
            self.assertIn('❌',call.args[1]['rich_message']['html'])

    def test_status_unknown_not_healthy_and_localized(self):
        data={'now':datetime.now(timezone.utc),'beats':{},'queues':{},'latency':{'samples':0,'seconds':None}}
        self.assertIn('COLLECTOR_STALE',incidents({**data,'queues':{k:{'uncertain':0,'dead_letter':0,'oldest_seconds':None} for k in ('channel','private')}}))
        data['queues']={k:{'uncertain':0,'dead_letter':0,'oldest_seconds':None,'pending':0,'held':0} for k in ('channel','private')}
        for lang, title in [('ru','Состояние системы'),('az','Sistemin vəziyyəti'),('en','System status')]:
            self.assertIn(title,render(data,lang))

    def test_status_reports_source_denial(self):
        now=datetime.now(timezone.utc)
        data={'now':now,'beats':{'collector':{'last_success_at':now,'details':{'phase':'source_blocked'}}},
              'queues':{k:{'uncertain':0,'dead_letter':0,'oldest_seconds':0} for k in ('channel','private')}}
        self.assertIn('BINA_ACCESS_DENIED',incidents(data))
