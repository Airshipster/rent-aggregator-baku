import os
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
import requests
from server import worker
from server.retention import fresh_for_delivery
from server.channel_policy import public_channel_eligible
from src.telegram_errors import TelegramAPIError


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.payload = {'deal_type':'rent','rent_period':'monthly','city':'Bakı',
            'category_slug':'menziller/yeni-tikili','updated_at':self.now.isoformat()}

    @patch.dict(os.environ,{'ENABLE_PUBLIC_CHANNEL':'true'})
    def test_channel_monthly_apartments_baku_only(self):
        self.assertTrue(public_channel_eligible(self.payload))
        for field,value in [('rent_period','daily'),('rent_period',None),('deal_type','sale'),
                            ('city','Xırdalan'),('category_slug','heyet-evleri')]:
            with self.subTest(field=field,value=value):
                self.assertFalse(public_channel_eligible({**self.payload,field:value}))

    def test_retention_bounds(self):
        self.assertTrue(fresh_for_delivery(self.payload,self.now,now=self.now))
        self.assertFalse(fresh_for_delivery(self.payload,self.now-timedelta(days=8),now=self.now))
        self.assertFalse(fresh_for_delivery({'updated_at':(self.now-timedelta(days=8)).isoformat()},now=self.now))
        self.assertFalse(fresh_for_delivery({},now=self.now))
        self.assertFalse(fresh_for_delivery({'updated_at':(self.now+timedelta(hours=1)).isoformat()},now=self.now))

    def run_error(self,error,queue='private',kind='send'):
        task={'id':'a','attempt_id':1,'attempts':1,'task_type':kind}
        with patch.object(worker,'delivery_cutoff',return_value=self.now),patch.object(worker,'claim',return_value=task),\
             patch.object(worker,'send',side_effect=error),patch.object(worker,'finish') as finish,patch.object(worker,'pause_bot') as pause:
            self.assertTrue(worker.process(queue))
            return finish.call_args.args[2],pause.call_count

    def test_lost_response_not_retried(self):
        self.assertEqual(self.run_error(requests.Timeout())[0],'uncertain')

    def test_private_removal_reply_lost_response_not_retried(self):
        self.assertEqual(self.run_error(requests.Timeout(),kind='mark_removed')[0],'uncertain')

    def test_429_pauses_both_delivery_workers(self):
        self.assertEqual(self.run_error(TelegramAPIError({'error_code':429,'parameters':{'retry_after':60}})),('failed',1))

    def test_blocked_user_no_endless_retries(self):
        self.assertEqual(self.run_error(TelegramAPIError({'error_code':403}))[0],'dead_letter')

    def test_definite_400_terminal(self):
        self.assertEqual(self.run_error(TelegramAPIError({'error_code':400}))[0],'dead_letter')

    def test_edit_timeout_can_retry(self):
        self.assertEqual(self.run_error(requests.Timeout(),queue='channel',kind='mark_removed')[0],'failed')

    def test_commit_failure_does_not_send_again(self):
        with patch.object(worker,'delivery_cutoff',return_value=self.now),patch.object(worker,'claim',return_value={'task_type':'send'}),\
             patch.object(worker,'send',return_value={'message_id':1}) as send,patch.object(worker,'finish',side_effect=RuntimeError('commit failed')):
            with self.assertRaises(RuntimeError): worker.process('private')
            self.assertEqual(send.call_count,1)


if __name__=='__main__': unittest.main()
