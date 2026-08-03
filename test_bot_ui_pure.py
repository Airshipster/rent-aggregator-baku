import sys
import types
import unittest


fake_db = types.ModuleType("server.db")
fake_db.connect = None
sys.modules.setdefault("server.db", fake_db)

from server import bot_ui


class BotUiPureTests(unittest.TestCase):
    def test_language_buttons_have_no_flags(self):
        labels = [label for row in bot_ui.LANGUAGE_BUTTONS for label, _value in row]
        self.assertEqual(labels, ["Русский", "Azərbaycanca", "English"])

    def test_range_is_human_readable(self):
        self.assertEqual(bot_ui._range_text("ru", 3, 7), "3–7")

    def test_clicking_selected_owner_removes_owner(self):
        values = {"owner", "agency"}
        self.assertEqual(bot_ui._toggled_values(values, "owner", values), {"agency"})

    def test_selecting_all_collapses_to_default(self):
        values = {"var", "yoxdur", "unknown"}
        self.assertIsNone(bot_ui._toggled_values({"var", "yoxdur"}, "unknown", values))

    def test_numeric_callbacks_fit_telegram_limit(self):
        filter_id = "00000000-0000-0000-0000-000000000000"
        rows = bot_ui._number_rows("ru", filter_id, "land_area_m2_min", ["1", "10", "100"])
        callbacks = [callback for row in rows for _label, callback in row]
        self.assertLessEqual(max(map(len, callbacks)), 64)

    def test_saved_filter_summary_shows_full_range(self):
        rule = {
            "name": "Новый фильтр",
            "basic": {
                "deal_type": ["rent"],
                "rent_period": ["monthly"],
                "category_key": "new",
                "category_slug": ["menziller/yeni-tikili"],
                "city": ["Bakı"],
                "rooms_min": 3,
                "rooms_max": 7,
            },
        }
        summary = bot_ui._filter_summary("ru", rule)
        self.assertIn("3–7 Комнаты".lower(), summary.lower())
        self.assertIn("Сделка: Аренда", summary)


if __name__ == "__main__":
    unittest.main()
