import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from server import bot_ui
from server import app as api
from fastapi import HTTPException
from server.matching import matches
from server.ranges import parse_range
from server.worker import delivery_cutoff, failure_status, retry_at
from src.telegram_client import TelegramClient
from src.telegram_errors import TelegramAPIError, redact_error
from src.utils import image_datetime, is_recent
from src.formatter_public_az import format_public
from src.formatter_private_rich import seller
from types import SimpleNamespace


class AuditRegressions(unittest.TestCase):
    def test_range_formats(self):
        for text,field,want in [
            ('с 7 по 15 этаж','floor',(7,15)),
            ('from 7 to 15 floors','floor',(7,15)),
            ('7 ilə 15 mərtəbə','floor',(7,15)),
            ('1 500 - 2 500 AZN','price',(1500,2500)),
            ('30,5-70.5 м²','area_m2',(30.5,70.5)),
            ('до 15','floor',(None,15)), ('7+','floor',(7,None)),
            ('7','floor',(7,7)), ('неважно','rooms',(None,None)),
            ('1-5 sot','land_area_m2',(1,5)),
        ]:
            with self.subTest(text=text): self.assertEqual(parse_range(text,field),want)

    def test_bad_ranges_are_not_silently_corrected(self):
        for value in ['15-7','-7','0','1.5','1,500','nan','inf','1 2','7-15-20','7 dollars']:
            with self.subTest(value=value), self.assertRaises(ValueError): parse_range(value,'floor')

    def test_range_screen_all_languages_and_callback_bytes(self):
        fid='00000000-0000-0000-0000-000000000001'
        for lang in ('ru','az','en'):
            for field in bot_ui.RANGE_FIELDS:
                with self.subTest(lang=lang,field=field), patch.object(bot_ui,'_get_filter',return_value={'basic':{}}), patch.object(bot_ui,'_user_language',return_value=lang), patch.object(bot_ui,'_screen') as screen:
                    cur=MagicMock()
                    bot_ui._range_screen(cur,1,1,fid,field,(3,7))
                    args=screen.call_args.args
                    callbacks=[callback for row in args[4] for _,callback in row]
                    self.assertTrue(any(x.startswith('rc:') for x in callbacks))
                    self.assertTrue(any(x.startswith('rb:') for x in callbacks))
                    self.assertTrue(all(len(x.encode())<=64 for x in callbacks))
                    self.assertFalse(any('UPDATE filters' in call.args[0] for call in cur.execute.call_args_list))

    def test_floors_not_in_required_wizard(self):
        cur=MagicMock(); cur.fetchone.return_value={'basic':{'category_key':'new','city':['Bakı']}}
        self.assertEqual(bot_ui._number_next_step(cur,'unused','area_m2_max'),'district')

    def test_unknown_optional_not_false(self):
        self.assertTrue(matches({}, {}, {'repair_status':{'values':['var']}}))
        self.assertFalse(matches({'repair_status':'yoxdur'}, {}, {'repair_status':{'values':['var']}}))
        self.assertFalse(matches({}, {}, {'repair_status':{'values':['var'],'include_unknown':False}}))
        self.assertTrue(matches({'repair_status':'var'}, {}, {'repair_status':{'include_unknown':False}}))

    def test_missing_and_future_dates_not_fresh(self):
        self.assertFalse(is_recent(None,24))
        self.assertFalse(is_recent(datetime.now(timezone.utc)+timedelta(days=1),24))
        self.assertIsNone(image_datetime('https://example.test/uploads/full/2026/99/20/10/00/a.jpg'))

    @patch.dict(os.environ,{},clear=True)
    def test_delivery_defaults_to_paused(self):
        self.assertIsNone(delivery_cutoff())
        os.environ['DELIVERY_ENABLED']='true'
        with self.assertRaises(ValueError): delivery_cutoff()
        os.environ['DELIVERY_NOT_BEFORE']='2026-09-13T00:00:00Z'
        self.assertIsNotNone(delivery_cutoff())

    def test_403_terminal_and_429_delayed(self):
        self.assertEqual(failure_status(1,TelegramAPIError({'error_code':403})),'dead_letter')
        error=TelegramAPIError({'error_code':429,'parameters':{'retry_after':120}})
        self.assertEqual(failure_status(188,error),'failed')
        self.assertGreater((retry_at(1,error)-datetime.now(timezone.utc)).total_seconds(),120)
        self.assertEqual(failure_status(8,RuntimeError('broken')),'dead_letter')

    @patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':'test'})
    def test_worker_client_does_not_sleep_or_retry_inline(self):
        client=TelegramClient(defer_retries=True)
        client.session=MagicMock()
        response=client.session.post.return_value
        response.status_code=429
        response.json.return_value={'ok':False,'error_code':429,'parameters':{'retry_after':60}}
        with patch('src.telegram_client.time.sleep') as sleep, self.assertRaises(TelegramAPIError):
            client.call('sendMessage',{})
        sleep.assert_not_called()
        self.assertEqual(client.session.post.call_count,1)

    def test_error_redaction(self):
        self.assertNotIn('123456789:',redact_error('https://api.telegram.org/bot123456789:abcdefghijklmnopqrstuvw/sendMessage'))

    def test_unknown_seller_not_mislabeled_owner(self):
        self.assertEqual(seller(SimpleNamespace(seller_type='unknown')),'#naməlum')

    def test_daily_rental_not_labeled_monthly(self):
        item=SimpleNamespace(landmarks=[],metro=None,district=None,rooms=2,seller_type='owner',category_slug='menziller/yeni-tikili',price=50,currency='AZN',rent_period='daily',area_m2=60,floor=2,total_floors=5,repair_status=None,listing_url='https://example.test/1')
        self.assertIn(' / gün',format_public(item))
        self.assertNotIn(' / ay',format_public(item))

    @patch.dict(os.environ,{},clear=True)
    def test_missing_ingest_cannot_start_legacy_broadcast(self):
        from src.main import main
        with self.assertRaises(RuntimeError): main()

    def test_idempotency_key_reuse_checks_digest(self):
        conn=MagicMock()
        cur=conn.__enter__.return_value.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect=[None,{'body_sha256':'different'}]
        with patch.object(api,'connect',return_value=conn),self.assertRaises(HTTPException) as caught:
            api._store_ingest(b'{"listings":[]}','existing')
        self.assertEqual(caught.exception.status_code,409)

    def test_foreign_wizard_cannot_modify_filter(self):
        cur=MagicMock()
        with patch.object(bot_ui,'_get_filter',return_value=None):
            bot_ui._wizard_callback(cur,1,1,'wf:00000000-0000-0000-0000-000000000001:deal:sale')
        cur.execute.assert_not_called()


if __name__=='__main__': unittest.main()
