import json
import os
import re
from html import escape
from typing import Any

import requests

from .db import connect
from .i18n import t
from .matching import matches
from .locations import CITIES, CITY_BY_ID


LANGUAGE_BUTTONS = [[("Русский", "ru"), ("Azərbaycanca", "az"), ("English", "en")]]
CATEGORIES = {
    "new": ("Новостройка", "menziller/yeni-tikili"),
    "old": ("Вторичка", "menziller/kohne-tikili"),
    "house": ("Дом/вилла", "heyet-evleri"),
    "office": ("Офис", "ofisler"),
    "garage": ("Гараж", "qarajlar"),
    "land": ("Земля", "torpaq"),
    "commercial": ("Коммерция", "obyektler"),
}
DISTRICTS = {
    "any": ("Bakı", None),
    "absheron": ("Abşeron", "Abşeron r."),
    "binagadi": ("Binəqədi", "Binəqədi r."),
    "khatai": ("Xətai", "Xətai r."),
    "khazar": ("Xəzər", "Xəzər r."),
    "garadagh": ("Qaradağ", "Qaradağ r."),
    "narimanov": ("Nərimanov", "Nərimanov r."),
    "nasimi": ("Nəsimi", "Nəsimi r."),
    "nizami": ("Nizami", "Nizami r."),
    "pirallahi": ("Pirallahı", "Pirallahı r."),
    "sabunchu": ("Sabunçu", "Sabunçu r."),
    "sabail": ("Səbail", "Səbail r."),
    "surakhani": ("Suraxanı", "Suraxanı r."),
    "yasamal": ("Yasamal", "Yasamal r."),
}

UI={
"ru":{"menu":"Меню","choose":"Выберите действие","configure":"Настроить фильтр","filters":"Мои фильтры","additional":"Дополнительные условия","settings":"Настройки","language":"Язык","payment":"Оплата","requests":"Заявки на доступ","access":"Управление доступом","back":"Назад","cancel":"Отмена","deal":"Что вас интересует?","rent":"Аренда","sale":"Покупка","period":"На какой срок нужна аренда?","monthly":"Помесячно","daily":"Посуточно","category":"Тип объекта","new":"Новостройка","old":"Вторичка","house":"Дом/вилла","office":"Офис","land":"Земля","commercial":"Коммерция","garage":"Гараж","pmin":"Цена от, AZN","pmax":"Цена до, AZN","no_min":"Без минимума","no_max":"Без максимума","rooms":"Количество комнат","any":"Любое","amin":"Площадь от, м²","amax":"Площадь до, м²","district":"Район","all_baku":"Весь Баку","saved":"Фильтр сохранён","found":"Найдено объявлений за сегодня: {count}.","none_today":"Подходящих объявлений за сегодня пока нет.","main":"Главное меню","no_filters":"Фильтров пока нет.","choose_filter":"Выберите фильтр","payment_off":"Оплата пока недоступна. Доступ выдаётся вручную.","no_requests":"Новых заявок нет.","open":"Открыть меню"},
"az":{"menu":"Menyu","choose":"Əməliyyatı seçin","configure":"Filtri tənzimlə","filters":"Filtrlərim","additional":"Əlavə şərtlər","settings":"Ayarlar","language":"Dil","payment":"Ödəniş","requests":"Giriş müraciətləri","access":"Girişin idarə edilməsi","back":"Geri","cancel":"Ləğv et","deal":"Sizi nə maraqlandırır?","rent":"Kirayə","sale":"Alış","period":"Kirayə müddəti","monthly":"Aylıq","daily":"Günlük","category":"Əmlak növü","new":"Yeni tikili","old":"Köhnə tikili","house":"Həyət evi/Villa","office":"Ofis","land":"Torpaq","commercial":"Obyekt","garage":"Qaraj","pmin":"Minimum qiymət, AZN","pmax":"Maksimum qiymət, AZN","no_min":"Minimum yoxdur","no_max":"Maksimum yoxdur","rooms":"Otaq sayı","any":"Fərqi yoxdur","amin":"Minimum sahə, m²","amax":"Maksimum sahə, m²","district":"Rayon","all_baku":"Bütün Bakı","saved":"Filtr yadda saxlanıldı","found":"Bu gün üçün {count} elan tapıldı.","none_today":"Bu gün üçün uyğun elan yoxdur.","main":"Əsas menyu","no_filters":"Hələ filtr yoxdur.","choose_filter":"Filtri seçin","payment_off":"Ödəniş hələ aktiv deyil. Giriş əl ilə verilir.","no_requests":"Yeni müraciət yoxdur.","open":"Menyunu aç"},
"en":{"menu":"Menu","choose":"Choose an action","configure":"Configure filter","filters":"My filters","additional":"Additional conditions","settings":"Settings","language":"Language","payment":"Payment","requests":"Access requests","access":"Access management","back":"Back","cancel":"Cancel","deal":"What are you looking for?","rent":"Rent","sale":"Buy","period":"Rental period","monthly":"Monthly","daily":"Daily","category":"Property type","new":"New building","old":"Old building","house":"House/Villa","office":"Office","land":"Land","commercial":"Commercial","garage":"Garage","pmin":"Minimum price, AZN","pmax":"Maximum price, AZN","no_min":"No minimum","no_max":"No maximum","rooms":"Number of rooms","any":"Any","amin":"Minimum area, m²","amax":"Maximum area, m²","district":"District","all_baku":"All Baku","saved":"Filter saved","found":"{count} matching listings found today.","none_today":"No matching listings found today.","main":"Main menu","no_filters":"No filters yet.","choose_filter":"Choose a filter","payment_off":"Payment is not available yet. Access is granted manually.","no_requests":"No new requests.","open":"Open menu"}}

UI["ru"].update({
    "area_any":"Любая", "done":"Готово", "seller":"Кто разместил", "repair":"Ремонт",
    "additional_warning":"Авторы часто не заполняют эти поля. Строгий вариант исключит объявления, где значение не указано.",
    "seller_question":"Кто разместил?", "repair_question":"Ремонт", "any_seller":"Любой",
    "owner_unknown":"Владелец, неизвестные допускаются", "owner_strict":"Только явно владелец",
    "agency_unknown":"Агентство, неизвестные допускаются", "agency_strict":"Только явно агентство",
    "any_repair":"Любой", "repair_unknown":"С ремонтом, неизвестные допускаются",
    "repair_strict":"Только явно с ремонтом", "no_repair":"Без ремонта",
    "new_filter":"Новый фильтр", "language_prompt":"Выберите язык · Dili seçin · Choose language",
    "district_nasimi":"Насиминский", "district_nizami":"Низаминский", "district_narimanov":"Наримановский",
    "district_yasamal":"Ясамальский", "district_sabail":"Сабаильский", "district_khatai":"Хатаинский",
    "district_binagadi":"Бинагадинский", "district_surakhani":"Сураханский", "district_sabunchu":"Сабунчинский",
    "access_add":"Добавить пользователя", "access_block":"Заблокировать", "access_rules":"Список правил",
    "choose_identifier_add":"Выберите идентификатор для добавления", "choose_identifier_block":"Выберите идентификатор для блокировки", "phone":"Телефон",
    "access_updated":"Доступ обновлён", "access_added":"добавлен", "access_blocked":"заблокирован",
    "rule_later":"Правило применится, когда пользователь идентифицируется в боте.", "recognize_failed":"Не удалось распознать значение", "try_again":"Попробуйте ещё раз.",
    "request_title":"Новая заявка на доступ", "name":"Имя", "not_set":"Не указано", "approve":"Одобрить", "reject":"Отклонить",
    "send_identifier":"Отправьте ID, username или телефон одним сообщением.", "send_block_identifier":"Отправьте значение, которое нужно заблокировать.",
    "rules_title":"Правила доступа", "rules_empty":"Правил пока нет.", "allowed":"разрешён", "blocked":"заблокирован",
    "filter_ready":"Фильтр настроен", "activate":"Сохранить и включить",
    "city":"Город по умолчанию", "city_prompt":"Выберите город для новых фильтров", "city_saved":"Город по умолчанию: {city}",
    "land_min":"Участок от, соток", "land_max":"Участок до, соток",
    "all_options":"Все варианты", "owner":"Владелец", "agency":"Агентство", "renovated":"С ремонтом", "not_renovated":"Без ремонта", "unknown":"Не указано",
    "choose_one_or_both":"Выберите один или оба варианта.", "optional_field":"Это поле необязательно на Bina.az. Автор мог его не заполнить.",
    "grant_access":"Дать доступ", "revoke_access":"Отозвать доступ", "confirm_access":"Подтвердите действие", "current_access":"Текущий доступ", "active":"активен", "inactive":"не выдан",
    "identifier_type_prompt":"Это Telegram ID или номер телефона?", "as_telegram_id":"Telegram ID", "as_phone":"Номер телефона",
})
UI["az"].update({
    "area_any":"Fərqi yoxdur", "done":"Hazırdır", "seller":"Elanı kim yerləşdirib", "repair":"Təmir",
    "additional_warning":"Müəlliflər bu sahələri çox vaxt doldurmurlar. Sərt şərt dəyəri göstərilməyən elanları istisna edəcək.",
    "seller_question":"Elanı kim yerləşdirib?", "repair_question":"Təmir", "any_seller":"Fərqi yoxdur",
    "owner_unknown":"Mülkiyyətçi, naməlumlar daxildir", "owner_strict":"Yalnız açıq şəkildə mülkiyyətçi",
    "agency_unknown":"Agentlik, naməlumlar daxildir", "agency_strict":"Yalnız açıq şəkildə agentlik",
    "any_repair":"Fərqi yoxdur", "repair_unknown":"Təmirli, naməlumlar daxildir",
    "repair_strict":"Yalnız açıq şəkildə təmirli", "no_repair":"Təmirsiz",
    "new_filter":"Yeni filtr", "language_prompt":"Выберите язык · Dili seçin · Choose language",
    "district_nasimi":"Nəsimi", "district_nizami":"Nizami", "district_narimanov":"Nərimanov",
    "district_yasamal":"Yasamal", "district_sabail":"Səbail", "district_khatai":"Xətai",
    "district_binagadi":"Binəqədi", "district_surakhani":"Suraxanı", "district_sabunchu":"Sabunçu",
    "access_add":"İstifadəçi əlavə et", "access_block":"Blokla", "access_rules":"Qaydaların siyahısı",
    "choose_identifier_add":"Əlavə etmək üçün identifikatoru seçin", "choose_identifier_block":"Bloklamaq üçün identifikatoru seçin", "phone":"Telefon",
    "access_updated":"Giriş yeniləndi", "access_added":"əlavə edildi", "access_blocked":"bloklandı",
    "rule_later":"Qayda istifadəçi botda identifikasiya olunduqda tətbiq ediləcək.", "recognize_failed":"Dəyəri tanımaq mümkün olmadı", "try_again":"Yenidən cəhd edin.",
    "request_title":"Yeni giriş müraciəti", "name":"Ad", "not_set":"Göstərilməyib", "approve":"Təsdiqlə", "reject":"Rədd et",
    "send_identifier":"ID, username və ya telefonu bir mesajla göndərin.", "send_block_identifier":"Bloklanacaq dəyəri göndərin.",
    "rules_title":"Giriş qaydaları", "rules_empty":"Hələ qayda yoxdur.", "allowed":"icazə verilib", "blocked":"bloklanıb",
    "filter_ready":"Filtr tənzimləndi", "activate":"Yadda saxla və aktiv et",
    "city":"Standart şəhər", "city_prompt":"Yeni filtrlər üçün şəhəri seçin", "city_saved":"Standart şəhər: {city}",
    "land_min":"Torpaq sahəsi, minimum sot", "land_max":"Torpaq sahəsi, maksimum sot",
    "all_options":"Bütün variantlar", "owner":"Mülkiyyətçi", "agency":"Agentlik", "renovated":"Təmirli", "not_renovated":"Təmirsiz", "unknown":"Göstərilməyib",
    "choose_one_or_both":"Bir və ya hər iki variantı seçin.", "optional_field":"Bu sahə Bina.az-da məcburi deyil. Müəllif onu doldurmaya bilər.",
    "grant_access":"Giriş ver", "revoke_access":"Girişi ləğv et", "confirm_access":"Əməliyyatı təsdiqləyin", "current_access":"Cari giriş", "active":"aktivdir", "inactive":"verilməyib",
    "identifier_type_prompt":"Bu Telegram ID-dir, yoxsa telefon nömrəsi?", "as_telegram_id":"Telegram ID", "as_phone":"Telefon nömrəsi",
})
UI["en"].update({
    "area_any":"Any", "done":"Done", "seller":"Posted by", "repair":"Renovation",
    "additional_warning":"Authors often leave these fields empty. A strict condition excludes listings where the value is not specified.",
    "seller_question":"Who posted it?", "repair_question":"Renovation", "any_seller":"Any",
    "owner_unknown":"Owner, including unknown", "owner_strict":"Explicitly owner only",
    "agency_unknown":"Agency, including unknown", "agency_strict":"Explicitly agency only",
    "any_repair":"Any", "repair_unknown":"Renovated, including unknown",
    "repair_strict":"Explicitly renovated only", "no_repair":"Not renovated",
    "new_filter":"New filter", "language_prompt":"Выберите язык · Dili seçin · Choose language",
    "district_nasimi":"Nasimi", "district_nizami":"Nizami", "district_narimanov":"Narimanov",
    "district_yasamal":"Yasamal", "district_sabail":"Sabail", "district_khatai":"Khatai",
    "district_binagadi":"Binagadi", "district_surakhani":"Surakhani", "district_sabunchu":"Sabunchu",
    "access_add":"Add user", "access_block":"Block", "access_rules":"Rules list",
    "choose_identifier_add":"Choose an identifier to add", "choose_identifier_block":"Choose an identifier to block", "phone":"Phone",
    "access_updated":"Access updated", "access_added":"added", "access_blocked":"blocked",
    "rule_later":"The rule will apply when the user identifies themselves in the bot.", "recognize_failed":"Could not recognize the value", "try_again":"Try again.",
    "request_title":"New access request", "name":"Name", "not_set":"Not specified", "approve":"Approve", "reject":"Reject",
    "send_identifier":"Send the ID, username, or phone number in one message.", "send_block_identifier":"Send the value to block.",
    "rules_title":"Access rules", "rules_empty":"No rules yet.", "allowed":"allowed", "blocked":"blocked",
    "filter_ready":"Filter configured", "activate":"Save and enable",
    "city":"Default city", "city_prompt":"Choose a city for new filters", "city_saved":"Default city: {city}",
    "land_min":"Land area from, sot", "land_max":"Land area to, sot",
    "all_options":"All options", "owner":"Owner", "agency":"Agency", "renovated":"Renovated", "not_renovated":"Not renovated", "unknown":"Not specified",
    "choose_one_or_both":"Select one or both options.", "optional_field":"This field is optional on Bina.az. The author may leave it empty.",
    "grant_access":"Grant access", "revoke_access":"Revoke access", "confirm_access":"Confirm the action", "current_access":"Current access", "active":"active", "inactive":"not granted",
    "identifier_type_prompt":"Is this a Telegram ID or a phone number?", "as_telegram_id":"Telegram ID", "as_phone":"Phone number",
})


def _l(language:str,key:str,**values:Any)->str:
    return UI.get(language,UI["ru"]).get(key,UI["ru"].get(key,key)).format(**values)


def _user_language(cur,uid:int)->str:
    cur.execute("SELECT language FROM users WHERE telegram_user_id=%s",(uid,)); row=cur.fetchone(); return (row or {}).get("language") or "ru"


def _normalize_identifier(kind: str, value: str) -> str:
    value=value.strip()
    if kind=="telegram_id":
        digits="".join(re.findall(r"\d",value))
        if not digits or len(digits)>20: raise ValueError("Некорректный Telegram ID")
        return digits
    if kind=="username":
        value=re.sub(r"^https?://t\.me/","",value,flags=re.I).lstrip("@").strip().lower()
        if not re.fullmatch(r"[a-z0-9_]{5,32}",value): raise ValueError("Некорректный username")
        return value
    digits="".join(re.findall(r"\d",value))
    if digits.startswith("00"): digits=digits[2:]
    if digits.startswith("0") and len(digits)==10: digits="994"+digits[1:]
    elif len(digits)==9: digits="994"+digits
    if not 7<=len(digits)<=15: raise ValueError("Некорректный номер телефона")
    return "+"+digits


def _apply_identifier_decision(cur, uid: int, user: dict[str,Any]) -> None:
    candidates=[("telegram_id",str(uid))]
    if user.get("username"): candidates.append(("username",user["username"].lower()))
    if user.get("phone_normalized"): candidates.append(("phone",user["phone_normalized"]))
    decisions=[]
    for kind,value in candidates:
        cur.execute("SELECT decision FROM access_identifiers WHERE identifier_type=%s AND normalized_value=%s",(kind,value)); row=cur.fetchone()
        if row:
            decisions.append(row["decision"])
            cur.execute("UPDATE access_identifiers SET linked_telegram_user_id=%s,updated_at=now() WHERE identifier_type=%s AND normalized_value=%s",(uid,kind,value))
    if decisions:
        # A block always wins over an approval attached to another identifier.
        state="deactivated" if "blocked" in decisions else "approved"
        cur.execute("UPDATE users SET state=%s,updated_at=now(),deactivated_at=CASE WHEN %s='deactivated' THEN now() ELSE NULL END WHERE telegram_user_id=%s",(state,state,uid))


def _store_access_decision(cur, admin_id: int, kind: str, raw: str, decision: str) -> tuple[str,int|None]:
    normalized=_normalize_identifier(kind,raw); display=("@"+normalized if kind=="username" else normalized)
    linked=None
    if kind=="telegram_id":
        linked=int(normalized)
        cur.execute("""INSERT INTO users(telegram_user_id,chat_id,state,language) VALUES(%s,%s,%s,'ru')
          ON CONFLICT(telegram_user_id) DO UPDATE SET state=EXCLUDED.state,updated_at=now(),deactivated_at=CASE WHEN EXCLUDED.state='deactivated' THEN now() ELSE NULL END""",(linked,linked,"approved" if decision=="approved" else "deactivated"))
    elif kind=="username":
        cur.execute("SELECT telegram_user_id FROM users WHERE lower(username)=%s",(normalized,)); row=cur.fetchone(); linked=row["telegram_user_id"] if row else None
    else:
        cur.execute("SELECT telegram_user_id FROM users WHERE phone_normalized=%s",(normalized,)); row=cur.fetchone(); linked=row["telegram_user_id"] if row else None
    if linked and kind!="telegram_id":
        state="approved" if decision=="approved" else "deactivated"
        cur.execute("UPDATE users SET state=%s,updated_at=now(),deactivated_at=CASE WHEN %s='deactivated' THEN now() ELSE NULL END WHERE telegram_user_id=%s",(state,state,linked))
    cur.execute("""INSERT INTO access_identifiers(identifier_type,normalized_value,display_value,decision,linked_telegram_user_id,actor_telegram_user_id)
      VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(identifier_type,normalized_value) DO UPDATE SET display_value=EXCLUDED.display_value,decision=EXCLUDED.decision,linked_telegram_user_id=COALESCE(EXCLUDED.linked_telegram_user_id,access_identifiers.linked_telegram_user_id),actor_telegram_user_id=EXCLUDED.actor_telegram_user_id,updated_at=now()""",(kind,normalized,display,decision,linked,admin_id))
    cur.execute("INSERT INTO access_identifier_audit(identifier_type,normalized_value,action,actor_telegram_user_id,linked_telegram_user_id) VALUES(%s,%s,%s,%s,%s)",(kind,normalized,decision,admin_id,linked))
    if linked:
        cur.execute("INSERT INTO user_access_audit(telegram_user_id,action,actor_telegram_user_id,details) VALUES(%s,%s,%s,%s::jsonb)",(linked,"manual_"+decision,admin_id,json.dumps({"identifier_type":kind,"identifier":display})))
    return display,linked


def _infer_identifier(raw: str) -> tuple[str, str]:
    value = raw.strip()
    if value.startswith("@") or re.match(r"^https?://t\.me/", value, re.I):
        return "username", value
    digits = "".join(re.findall(r"\d", value))
    if value.startswith(("+", "00", "0")) or (digits.startswith("994") and len(digits) in (12, 13)):
        return "phone", value
    if re.fullmatch(r"\d{5,20}", value):
        return "telegram_id", value
    raise ValueError("Unrecognized identifier")


def _access_confirmation(
    cur,
    admin_id: int,
    chat_id: int,
    identifiers: list[tuple[str, str]],
    supplied: dict[str, Any] | None = None,
) -> None:
    supplied = supplied or {}
    normalized: list[dict[str, str]] = []
    linked_id = int(supplied.get("user_id") or 0) or None
    decision = None
    for kind, raw in identifiers:
        value = _normalize_identifier(kind, raw)
        display = "@" + value if kind == "username" else value
        normalized.append({"kind": kind, "value": value, "display": display})
        cur.execute(
            "SELECT decision,linked_telegram_user_id FROM access_identifiers WHERE identifier_type=%s AND normalized_value=%s",
            (kind, value),
        )
        rule = cur.fetchone()
        if rule:
            decision = rule["decision"]
            linked_id = linked_id or rule.get("linked_telegram_user_id")
    account = None
    if linked_id:
        cur.execute(
            "SELECT telegram_user_id,first_name,last_name,username,phone_normalized,state FROM users WHERE telegram_user_id=%s",
            (linked_id,),
        )
        account = cur.fetchone()
    if not account:
        for item in normalized:
            if item["kind"] == "username":
                cur.execute("SELECT telegram_user_id,first_name,last_name,username,phone_normalized,state FROM users WHERE lower(username)=%s", (item["value"],))
            elif item["kind"] == "phone":
                cur.execute("SELECT telegram_user_id,first_name,last_name,username,phone_normalized,state FROM users WHERE phone_normalized=%s", (item["value"],))
            else:
                continue
            account = cur.fetchone()
            if account:
                linked_id = account["telegram_user_id"]
                break
    active = bool((account and account["state"] == "approved") or decision == "approved") and decision != "blocked"
    action = "blocked" if active else "approved"
    language = _user_language(cur, admin_id)
    first_name = supplied.get("first_name") or (account or {}).get("first_name")
    last_name = supplied.get("last_name") or (account or {}).get("last_name")
    username = supplied.get("username") or (account or {}).get("username")
    phone = supplied.get("phone_number") or (account or {}).get("phone_normalized")
    name = " ".join(x for x in (first_name, last_name) if x) or _l(language, "not_set")
    lines = [f"<b>{_l(language, 'confirm_access')}</b>"]
    if linked_id:
        lines.append(f"ID: <code>{linked_id}</code>")
    if username:
        lines.append(f"Username: @{escape(str(username).lstrip('@'))}")
    lines.append(f"{_l(language, 'name')}: {escape(name)}")
    if phone:
        lines.append(f"{_l(language, 'phone')}: <code>{escape(str(phone))}</code>")
    lines.append(f"{_l(language, 'current_access')}: {_l(language, 'active' if active else 'inactive')}")
    cur.execute(
        "UPDATE users SET wizard=%s::jsonb WHERE telegram_user_id=%s",
        (json.dumps({"await": "access_confirmation", "decision": action, "identifiers": normalized}), admin_id),
    )
    button = _l(language, "revoke_access" if active else "grant_access")
    _screen(cur, admin_id, chat_id, "\n".join(lines), [[(button, f"access:confirm:{action}")], [(_l(language, "cancel"), "settings:access")]])


def _tg(method: str, payload: dict[str, Any]) -> Any:
    response = requests.post(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}",
        json=payload,
        timeout=20,
    )
    data = response.json()
    if not data.get("ok"):
        description = data.get("description", "Telegram API error")
        if "message is not modified" in description:
            return {}
        raise RuntimeError(description)
    return data["result"]


def _keyboard(rows: list[list[tuple[str, str]]]) -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": label, "callback_data": data} for label, data in row] for row in rows]}


def _screen(cur, user_id: int, chat_id: int, text: str, rows: list[list[tuple[str, str]]], kind: str = "menu") -> None:
    cur.execute("SELECT menu_message_id FROM users WHERE telegram_user_id=%s", (user_id,))
    message_id = (cur.fetchone() or {}).get("menu_message_id")
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "reply_markup": _keyboard(rows)}
    if message_id:
        try:
            _tg("editMessageText", {**payload, "message_id": message_id})
            return
        except RuntimeError:
            pass
    message = _tg("sendMessage", payload)
    message_id = message["message_id"]
    cur.execute("UPDATE users SET menu_message_id=%s WHERE telegram_user_id=%s", (message_id, user_id))
    cur.execute(
        """INSERT INTO bot_messages(telegram_user_id,chat_id,telegram_message_id,kind)
        VALUES(%s,%s,%s,%s) ON CONFLICT(chat_id,telegram_message_id) DO NOTHING""",
        (user_id, chat_id, message_id, kind),
    )


def _ensure_launcher(cur, user_id: int, chat_id: int) -> int:
    cur.execute("SELECT pinned_menu_message_id,menu_pinned_at FROM users WHERE telegram_user_id=%s", (user_id,))
    row=cur.fetchone() or {}; message_id=row.get("pinned_menu_message_id")
    language=_user_language(cur,user_id)
    payload={"chat_id":chat_id,"text":f"<b>{_l(language,'menu')}</b>","parse_mode":"HTML","reply_markup":_keyboard([[(_l(language,'open'),"launcher:open")]])}
    if message_id:
        try:
            _tg("editMessageText",{**payload,"message_id":message_id})
            cur.execute("""UPDATE bot_messages SET kind='pinned_launcher'
              WHERE telegram_user_id=%s AND telegram_message_id=%s""",(user_id,message_id))
            return message_id
        except RuntimeError:
            message_id=None
    message=_tg("sendMessage",payload); message_id=message["message_id"]
    cur.execute("UPDATE users SET pinned_menu_message_id=%s,menu_pinned_at=now() WHERE telegram_user_id=%s",(message_id,user_id))
    cur.execute("""INSERT INTO bot_messages(telegram_user_id,chat_id,telegram_message_id,kind)
      VALUES(%s,%s,%s,'pinned_launcher') ON CONFLICT(chat_id,telegram_message_id) DO NOTHING""",(user_id,chat_id,message_id))
    _tg("pinChatMessage",{"chat_id":chat_id,"message_id":message_id,"disable_notification":True})
    return message_id


def _reset_active(cur, user_id: int, chat_id: int) -> None:
    cur.execute("SELECT menu_message_id,pinned_menu_message_id FROM users WHERE telegram_user_id=%s",(user_id,)); row=cur.fetchone() or {}
    message_id=row.get("menu_message_id")
    if message_id and message_id != row.get("pinned_menu_message_id"):
        try:
            _tg("deleteMessage",{"chat_id":chat_id,"message_id":message_id})
            cur.execute("UPDATE bot_messages SET status='deleted',deleted_at=now() WHERE chat_id=%s AND telegram_message_id=%s",(chat_id,message_id))
        except RuntimeError:
            pass
    cur.execute("UPDATE users SET menu_message_id=NULL WHERE telegram_user_id=%s",(user_id,))


def _language_screen(cur, uid: int, chat_id: int) -> None:
    _screen(cur, uid, chat_id, UI["ru"]["language_prompt"], [[(label, f"lang:{value}") for label, value in LANGUAGE_BUTTONS[0]]], "language")


def _main(cur, uid: int, chat_id: int, language: str) -> None:
    rows = [
        [(_l(language,"configure"), "filter:new")],
        [(_l(language,"filters"), "filter:list")],
        [(_l(language,"additional"), "additional:list")],
        [(_l(language,"settings"), "settings")],
    ]
    _screen(cur, uid, chat_id, _l(language,"choose"), rows)


def _settings(cur, uid: int, chat_id: int, admin: bool) -> None:
    language=_user_language(cur,uid)
    cur.execute("SELECT default_city_name FROM users WHERE telegram_user_id=%s", (uid,))
    city = (cur.fetchone() or {}).get("default_city_name") or "Bakı"
    rows = [[(_l(language,"language"), "settings:language")], [(f"{_l(language,'city')}: {city}", "settings:city:0")], [(_l(language,"payment"), "settings:payment")]]
    if admin:
        rows.append([(_l(language,"requests"), "settings:applications")])
        rows.append([(_l(language,"access"), "settings:access")])
    rows.append([(_l(language,"back"), "main")])
    _screen(cur, uid, chat_id, f"<b>{_l(language,'settings')}</b>", rows)


def _city_screen(cur, uid: int, chat_id: int, page: int) -> None:
    language = _user_language(cur, uid)
    page_size = 10
    page = max(0, min(page, (len(CITIES) - 1) // page_size))
    choices = CITIES[page * page_size:(page + 1) * page_size]
    rows = [[(name, f"city:set:{city_id}:{page}")] for city_id, name in choices]
    nav = []
    if page:
        nav.append(("‹", f"settings:city:{page - 1}"))
    if (page + 1) * page_size < len(CITIES):
        nav.append(("›", f"settings:city:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([(_l(language, "back"), "settings")])
    _screen(cur, uid, chat_id, f"<b>{_l(language, 'city_prompt')}</b>", rows)


def _access_screen(cur, uid: int, chat_id: int) -> None:
    language=_user_language(cur,uid)
    _screen(cur,uid,chat_id,f"<b>{_l(language,'access')}</b>",[
        [(_l(language,"access_add"),"access:add"),(_l(language,"access_block"),"access:block")],
        [(_l(language,"access_rules"),"access:list")],[(_l(language,"back"),"settings")]
    ])


def _identifier_type_screen(cur,uid:int,chat_id:int,decision:str)->None:
    language=_user_language(cur,uid)
    prompt=_l(language,"choose_identifier_add" if decision=="approved" else "choose_identifier_block")
    _screen(cur,uid,chat_id,prompt,[
        [("Telegram ID",f"access:{decision}:telegram_id")],
        [("Username",f"access:{decision}:username")],
        [(_l(language,"phone"),f"access:{decision}:phone")],[(_l(language,"back"),"settings:access")]
    ])


def _set_basic(cur, filter_id: str, uid: int, key: str, value: Any) -> bool:
    cur.execute("SELECT basic FROM filters WHERE id=%s AND telegram_user_id=%s AND deleted_at IS NULL", (filter_id, uid))
    row = cur.fetchone()
    if not row:
        return False
    basic = dict(row["basic"])
    if value is None:
        basic.pop(key, None)
    else:
        basic[key] = value
    cur.execute("UPDATE filters SET basic=%s::jsonb,updated_at=now() WHERE id=%s", (json.dumps(basic), filter_id))
    return True


def _enqueue_today(cur, uid: int, filter_id: str) -> int:
    cur.execute("SELECT basic,additional FROM filters WHERE id=%s AND telegram_user_id=%s AND deleted_at IS NULL",(filter_id,uid)); rule=cur.fetchone()
    if not rule: return 0
    cur.execute("SELECT chat_id FROM users WHERE telegram_user_id=%s AND state='approved'",(uid,)); account=cur.fetchone()
    if not account: return 0
    cur.execute("""SELECT id,payload FROM listings WHERE status='active'
      AND first_seen_at >= ((now() AT TIME ZONE 'Asia/Baku')::date AT TIME ZONE 'Asia/Baku')
      ORDER BY first_seen_at""")
    queued=0
    for item in cur.fetchall():
        if not matches(item["payload"],rule["basic"],rule["additional"]): continue
        cur.execute("""INSERT INTO deliveries(listing_id,telegram_user_id,chat_id) VALUES(%s,%s,%s)
          ON CONFLICT(listing_id,telegram_user_id) DO NOTHING RETURNING id""",(item["id"],uid,account["chat_id"])); delivery=cur.fetchone()
        if delivery:
            cur.execute("INSERT INTO outbox_tasks(delivery_id,task_type) VALUES(%s,'send') ON CONFLICT DO NOTHING",(delivery["id"],)); queued+=1
    return queued


def _wizard(cur, uid: int, chat_id: int, filter_id: str, step: str, context: dict[str, Any] | None = None) -> None:
    context = context or {}
    language = _user_language(cur, uid)
    back = [(_l(language, "cancel"), f"filter:cancel:{filter_id}")]
    if step == "deal":
        _screen(cur, uid, chat_id, f"<b>{_l(language, 'deal')}</b>", [[(_l(language, "rent"), f"wf:{filter_id}:deal:rent")], [(_l(language, "sale"), f"wf:{filter_id}:deal:sale")], back])
    elif step == "period":
        _screen(cur, uid, chat_id, f"<b>{_l(language, 'period')}</b>", [[(_l(language, "monthly"), f"wf:{filter_id}:period:monthly")], [(_l(language, "daily"), f"wf:{filter_id}:period:daily")], back])
    elif step == "category":
        cur.execute("SELECT basic FROM filters WHERE id=%s", (filter_id,)); basic = cur.fetchone()["basic"]
        daily = basic.get("rent_period") == ["daily"]
        keys = ["new", "old", "house"] if daily else list(CATEGORIES)
        rows = [[(_l(language, key), f"wf:{filter_id}:category:{key}")] for key in keys]
        rows.append(back)
        _screen(cur, uid, chat_id, f"<b>{_l(language, 'category')}</b>", rows)
    elif step == "price_min":
        values = [(_l(language, "no_min"), "any"), ("300", "300"), ("500", "500"), ("800", "800"), ("1000", "1000"), ("1500", "1500")]
        _screen(cur, uid, chat_id, f"<b>{_l(language, 'pmin')}</b>", [[(a, f"wf:{filter_id}:pmin:{b}") for a,b in values[:3]], [(a, f"wf:{filter_id}:pmin:{b}") for a,b in values[3:]], back])
    elif step == "price_max":
        values = [(_l(language, "no_max"), "any"), ("500", "500"), ("800", "800"), ("1000", "1000"), ("1500", "1500"), ("2500", "2500"), ("5000", "5000")]
        _screen(cur, uid, chat_id, f"<b>{_l(language, 'pmax')}</b>", [[(a, f"wf:{filter_id}:pmax:{b}") for a,b in values[:4]], [(a, f"wf:{filter_id}:pmax:{b}") for a,b in values[4:]], back])
    elif step == "rooms":
        values = [(_l(language, "any"), "any"), ("1", "1"), ("2", "2"), ("3", "3"), ("4+", "4")]
        _screen(cur, uid, chat_id, f"<b>{_l(language, 'rooms')}</b>", [[(a, f"wf:{filter_id}:rooms:{b}") for a,b in values], back])
    elif step == "area_min":
        cur.execute("SELECT basic FROM filters WHERE id=%s", (filter_id,)); basic = cur.fetchone()["basic"]
        land = basic.get("category_key") == "land"
        values = [(_l(language, "area_any"), "any"), ("30", "30"), ("50", "50"), ("70", "70"), ("100", "100"), ("200", "200")]
        _screen(cur, uid, chat_id, f"<b>{_l(language, 'land_min' if land else 'amin')}</b>", [[(a, f"wf:{filter_id}:amin:{b}") for a,b in values[:3]], [(a, f"wf:{filter_id}:amin:{b}") for a,b in values[3:]], back])
    elif step == "area_max":
        cur.execute("SELECT basic FROM filters WHERE id=%s", (filter_id,)); basic = cur.fetchone()["basic"]
        land = basic.get("category_key") == "land"
        values = [(_l(language, "area_any"), "any"), ("50", "50"), ("70", "70"), ("100", "100"), ("150", "150"), ("300", "300"), ("500", "500")]
        _screen(cur, uid, chat_id, f"<b>{_l(language, 'land_max' if land else 'amax')}</b>", [[(a, f"wf:{filter_id}:amax:{b}") for a,b in values[:4]], [(a, f"wf:{filter_id}:amax:{b}") for a,b in values[4:]], back])
    elif step == "district":
        rows = [[(_l(language, "all_baku") if key == "any" else label, f"wf:{filter_id}:district:{key}")] for key, (label, _value) in DISTRICTS.items()]
        rows.append(back)
        _screen(cur, uid, chat_id, f"<b>{_l(language, 'district')}</b>", rows)
    elif step == "done":
        _screen(cur, uid, chat_id, f"<b>{_l(language, 'filter_ready')}</b>", [[(_l(language, "additional"), f"additional:{filter_id}")], [(_l(language, "activate"), f"filter:activate:{filter_id}")]])


def _wizard_callback(cur, uid: int, chat_id: int, data: str) -> None:
    _, filter_id, step, value = data.split(":", 3)
    if step == "deal":
        _set_basic(cur, filter_id, uid, "deal_type", [value]); _wizard(cur, uid, chat_id, filter_id, "period" if value == "rent" else "category")
    elif step == "period":
        _set_basic(cur, filter_id, uid, "rent_period", [value]); _wizard(cur, uid, chat_id, filter_id, "category")
    elif step == "category":
        _set_basic(cur, filter_id, uid, "category_slug", [CATEGORIES[value][1]]); _set_basic(cur, filter_id, uid, "category_key", value); _wizard(cur, uid, chat_id, filter_id, "price_min")
    elif step == "pmin":
        _set_basic(cur, filter_id, uid, "price_min", None if value == "any" else int(value)); _wizard(cur, uid, chat_id, filter_id, "price_max")
    elif step == "pmax":
        _set_basic(cur, filter_id, uid, "price_max", None if value == "any" else int(value))
        cur.execute("SELECT basic FROM filters WHERE id=%s",(filter_id,)); basic=cur.fetchone()["basic"]
        _wizard(cur, uid, chat_id, filter_id, "rooms" if basic.get("category_key") in ("new","old","office") else "area_min")
    elif step == "rooms":
        _set_basic(cur, filter_id, uid, "rooms_min", None if value == "any" else int(value)); _wizard(cur, uid, chat_id, filter_id, "area_min")
    elif step == "amin":
        cur.execute("SELECT basic FROM filters WHERE id=%s",(filter_id,)); basic=cur.fetchone()["basic"]
        key="land_area_m2_min" if basic.get("category_key")=="land" else "area_m2_min"
        _set_basic(cur, filter_id, uid, key, None if value == "any" else int(value)); _wizard(cur, uid, chat_id, filter_id, "area_max")
    elif step == "amax":
        cur.execute("SELECT basic FROM filters WHERE id=%s",(filter_id,)); basic=cur.fetchone()["basic"]
        key="land_area_m2_max" if basic.get("category_key")=="land" else "area_m2_max"
        _set_basic(cur, filter_id, uid, key, None if value == "any" else int(value))
        cur.execute("SELECT basic FROM filters WHERE id=%s",(filter_id,)); basic=cur.fetchone()["basic"]
        _wizard(cur, uid, chat_id, filter_id, "district" if basic.get("city")==["Bakı"] else "done")
    elif step == "district":
        _set_basic(cur, filter_id, uid, "district", None if value == "any" else [DISTRICTS[value][1]]); _wizard(cur, uid, chat_id, filter_id, "done")


def _additional(cur, uid: int, chat_id: int, filter_id: str) -> None:
    language = _user_language(cur, uid)
    text = f"<b>{_l(language, 'additional')}</b>\n\n{_l(language, 'additional_warning')}"
    rows = [[(_l(language, "seller"), f"ad:{filter_id}:seller")], [(_l(language, "repair"), f"ad:{filter_id}:repair")], [(_l(language, "activate"), f"filter:activate:{filter_id}")]]
    _screen(cur, uid, chat_id, text, rows)


def _set_additional(cur, filter_id: str, uid: int, field: str, values: list[str] | None, strict: bool = False, include_unknown: bool | None = None) -> None:
    cur.execute("SELECT additional FROM filters WHERE id=%s AND telegram_user_id=%s", (filter_id, uid)); row=cur.fetchone()
    if not row: return
    additional=dict(row["additional"])
    if values is None: additional.pop(field, None)
    else:
        additional[field]={"values":values,"strict":strict}
        if include_unknown is not None:
            additional[field]["include_unknown"] = include_unknown
    cur.execute("UPDATE filters SET additional=%s::jsonb,updated_at=now() WHERE id=%s",(json.dumps(additional),filter_id))


def _selected_additional(cur, filter_id: str, uid: int, field: str, all_values: set[str]) -> set[str]:
    cur.execute("SELECT additional FROM filters WHERE id=%s AND telegram_user_id=%s", (filter_id, uid))
    row = cur.fetchone()
    rule = ((row or {}).get("additional") or {}).get(field)
    if not rule:
        return set(all_values)
    selected = set(rule.get("values") or [])
    if rule.get("include_unknown"):
        selected.add("unknown")
    return selected


def _toggle_additional(cur, filter_id: str, uid: int, field: str, value: str, all_values: set[str]) -> None:
    current = _selected_additional(cur, filter_id, uid, field, all_values)
    if value == "all":
        _set_additional(cur, filter_id, uid, field, None)
        return
    if current == all_values:
        current = {value}
    elif value in current:
        current.remove(value)
    else:
        current.add(value)
    if not current or current == all_values:
        _set_additional(cur, filter_id, uid, field, None)
    else:
        _set_additional(cur, filter_id, uid, field, sorted(current - {"unknown"}), include_unknown="unknown" in current)


def _choice_label(language: str, key: str, selected: bool) -> str:
    return ("✅ " if selected else "❌ ") + _l(language, key)


def _seller_screen(cur, uid: int, chat_id: int, filter_id: str) -> None:
    language = _user_language(cur, uid)
    selected = _selected_additional(cur, filter_id, uid, "seller_type", {"owner", "agency"})
    rows = [
        [(_choice_label(language, "owner", "owner" in selected), f"av:{filter_id}:seller:owner")],
        [(_choice_label(language, "agency", "agency" in selected), f"av:{filter_id}:seller:agency")],
        [(_l(language, "back"), f"additional:{filter_id}")],
    ]
    _screen(cur, uid, chat_id, f"<b>{_l(language, 'seller_question')}</b>\n{_l(language, 'choose_one_or_both')}", rows)


def _repair_screen(cur, uid: int, chat_id: int, filter_id: str) -> None:
    language = _user_language(cur, uid)
    all_values = {"var", "yoxdur", "unknown"}
    selected = _selected_additional(cur, filter_id, uid, "repair_status", all_values)
    rows = [
        [(_choice_label(language, "all_options", selected == all_values), f"av:{filter_id}:repair:all")],
        [(_choice_label(language, "renovated", "var" in selected), f"av:{filter_id}:repair:var")],
        [(_choice_label(language, "not_renovated", "yoxdur" in selected), f"av:{filter_id}:repair:yoxdur")],
        [(_choice_label(language, "unknown", "unknown" in selected), f"av:{filter_id}:repair:unknown")],
        [(_l(language, "back"), f"additional:{filter_id}")],
    ]
    _screen(cur, uid, chat_id, f"<b>{_l(language, 'repair_question')}</b>\n\n{_l(language, 'optional_field')}", rows)


def handle_update(update: dict[str, Any]) -> dict[str, bool]:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO telegram_updates(update_id) VALUES(%s) ON CONFLICT DO NOTHING RETURNING update_id", (update.get("update_id"),))
        if not cur.fetchone(): return {"ok": True}
        callback = update.get("callback_query") or {}
        message = update.get("message") or callback.get("message") or {}
        user = (update.get("message") or {}).get("from") or callback.get("from") or {}
        if not message or not user or user.get("is_bot"): return {"ok": True}
        uid, chat_id = int(user["id"]), int(message["chat"]["id"])
        cur.execute("""INSERT INTO users(telegram_user_id,chat_id,first_name,last_name,username) VALUES(%s,%s,%s,%s,%s)
          ON CONFLICT(telegram_user_id) DO UPDATE SET chat_id=EXCLUDED.chat_id,first_name=EXCLUDED.first_name,last_name=EXCLUDED.last_name,username=EXCLUDED.username,updated_at=now()""",(uid,chat_id,user.get("first_name"),user.get("last_name"),user.get("username")))
        if callback.get("id"):
            _tg("answerCallbackQuery", {"callback_query_id": callback["id"]})
        cur.execute("SELECT state,language,language_selected FROM users WHERE telegram_user_id=%s",(uid,)); profile=cur.fetchone()
        data, text = callback.get("data", ""), (update.get("message") or {}).get("text", "")
        admin_id=int(os.environ["TELEGRAM_ADMIN_USER_ID"])
        contact=(update.get("message") or {}).get("contact")
        cur.execute("SELECT wizard FROM users WHERE telegram_user_id=%s",(uid,)); wizard=(cur.fetchone() or {}).get("wizard") or {}
        if contact and uid == admin_id:
            identifiers=[]
            if contact.get("user_id"):
                identifiers.append(("telegram_id", str(contact["user_id"])))
            if contact.get("phone_number"):
                identifiers.append(("phone", contact["phone_number"]))
            if identifiers:
                _access_confirmation(cur, uid, chat_id, identifiers, contact)
                return {"ok": True}
        if contact and int(contact.get("user_id") or 0)==uid:
            try:
                phone=_normalize_identifier("phone",contact.get("phone_number") or "")
                cur.execute("UPDATE users SET phone_normalized=%s WHERE telegram_user_id=%s",(phone,uid))
                _apply_identifier_decision(cur,uid,{**user,"phone_normalized":phone})
            except ValueError:
                pass
        if text and uid==admin_id and wizard.get("await")=="access_identifier" and not text.startswith("/"):
            language=profile["language"]
            try:
                display,linked=_store_access_decision(cur,uid,wizard["kind"],text,wizard["decision"])
                cur.execute("UPDATE users SET wizard='{}'::jsonb WHERE telegram_user_id=%s",(uid,))
                result=_l(language,"access_added" if wizard["decision"]=="approved" else "access_blocked")
                suffix=f"\nTelegram ID: <code>{linked}</code>" if linked else "\n"+_l(language,"rule_later")
                _screen(cur,uid,chat_id,f"<b>{_l(language,'access_updated')}</b>\n{display}: {result}.{suffix}",[[(_l(language,'back'),'settings:access')]])
            except ValueError:
                _screen(cur,uid,chat_id,f"<b>{_l(language,'recognize_failed')}</b>\n{_l(language,'try_again')}",[[(_l(language,'cancel'),'settings:access')]])
            return {"ok":True}
        if text and uid == admin_id and not text.startswith("/") and not callback:
            try:
                if re.fullmatch(r"\d{9,12}", text.strip()) and not text.strip().startswith(("0", "994")):
                    cur.execute("SELECT 1 FROM users WHERE telegram_user_id=%s", (int(text.strip()),))
                    known_id = bool(cur.fetchone())
                    phone = _normalize_identifier("phone", text)
                    cur.execute("SELECT 1 FROM users WHERE phone_normalized=%s", (phone,))
                    known_phone = bool(cur.fetchone())
                    if not known_id and not known_phone:
                        cur.execute("UPDATE users SET wizard=%s::jsonb WHERE telegram_user_id=%s",(json.dumps({"await":"identifier_kind","raw":text.strip()}),uid))
                        language=profile["language"]
                        _screen(cur,uid,chat_id,_l(language,"identifier_type_prompt"),[[(_l(language,"as_telegram_id"),"access:identify:telegram_id")],[(_l(language,"as_phone"),"access:identify:phone")],[(_l(language,"cancel"),"settings:access")]])
                        return {"ok":True}
                    kind = "telegram_id" if known_id else "phone"
                    _access_confirmation(cur, uid, chat_id, [(kind, text)])
                    return {"ok": True}
                kind, raw = _infer_identifier(text)
                _access_confirmation(cur, uid, chat_id, [(kind, raw)])
                return {"ok": True}
            except ValueError:
                pass
        if text.startswith("/start"):
            _apply_identifier_decision(cur,uid,user)
            cur.execute("SELECT state,language,language_selected FROM users WHERE telegram_user_id=%s",(uid,)); profile=cur.fetchone()
            _ensure_launcher(cur,uid,chat_id); _reset_active(cur,uid,chat_id)
            if not profile["language_selected"]: _language_screen(cur,uid,chat_id)
            elif profile["state"]=="approved": _main(cur,uid,chat_id,profile["language"])
            else: _screen(cur,uid,chat_id,t(profile["language"],"closed"),[[(t(profile["language"],"apply"),"apply")]])
            return {"ok": True}
        if data=="launcher:open":
            _reset_active(cur,uid,chat_id)
            if not profile["language_selected"]: _language_screen(cur,uid,chat_id)
            elif profile["state"]=="approved": _main(cur,uid,chat_id,profile["language"])
            else: _screen(cur,uid,chat_id,t(profile["language"],"closed"),[[(t(profile["language"],"apply"),"apply")]])
            return {"ok":True}
        if data.startswith("lang:"):
            language=data.split(":",1)[1]; cur.execute("UPDATE users SET language=%s,language_selected=true WHERE telegram_user_id=%s",(language,uid))
            _ensure_launcher(cur,uid,chat_id)
            if profile["state"]=="approved": _main(cur,uid,chat_id,language)
            else: _screen(cur,uid,chat_id,t(language,"closed"),[[(t(language,"apply"),"apply")]])
        elif data=="apply":
            cur.execute("INSERT INTO user_access_audit(telegram_user_id,action) VALUES(%s,'application')",(uid,))
            _screen(cur,uid,chat_id,t(profile["language"],"sent"),[])
            admin_language=_user_language(cur,admin_id)
            name=" ".join(x for x in [user.get("first_name"),user.get("last_name")] if x) or _l(admin_language,"not_set")
            username=f"@{user.get('username')}" if user.get("username") else _l(admin_language,"not_set")
            request=_tg("sendMessage",{"chat_id":admin_id,"text":f"<b>{_l(admin_language,'request_title')}</b>\n\nID: <code>{uid}</code>\nUsername: {username}\n{_l(admin_language,'name')}: {name}","parse_mode":"HTML","reply_markup":_keyboard([[(_l(admin_language,"approve"),f"approve:{uid}"),(_l(admin_language,"reject"),f"reject:{uid}")]])})
            cur.execute("""INSERT INTO bot_messages(chat_id,telegram_message_id,kind)
              VALUES(%s,%s,'access_request_admin') ON CONFLICT(chat_id,telegram_message_id) DO NOTHING""",(admin_id,request["message_id"]))
        elif data.startswith(("approve:","reject:")) and uid==admin_id:
            action,target=data.split(":",1); state="approved" if action=="approve" else "rejected"
            cur.execute("UPDATE users SET state=%s WHERE telegram_user_id=%s",(state,int(target)))
            cur.execute("INSERT INTO user_access_audit(telegram_user_id,action,actor_telegram_user_id) VALUES(%s,%s,%s)",(int(target),state,uid))
            _settings(cur,uid,chat_id,True)
        elif profile["state"]!="approved":
            _screen(cur,uid,chat_id,t(profile["language"],"closed"),[[(t(profile["language"],"apply"),"apply")]])
        elif data=="main": _main(cur,uid,chat_id,profile["language"])
        elif data=="settings": _settings(cur,uid,chat_id,uid==admin_id)
        elif data=="settings:language": _language_screen(cur,uid,chat_id)
        elif data.startswith("settings:city:"):
            _city_screen(cur,uid,chat_id,int(data.rsplit(":",1)[1]))
        elif data.startswith("city:set:"):
            _,_,city_id,_page=data.split(":",3); city_id=int(city_id); city_name=CITY_BY_ID[city_id]
            cur.execute("UPDATE users SET default_city_id=%s,default_city_name=%s WHERE telegram_user_id=%s",(city_id,city_name,uid))
            _screen(cur,uid,chat_id,_l(profile["language"],"city_saved",city=city_name),[[(_l(profile["language"],"back"),"settings")]])
        elif data=="settings:payment":
            language=profile["language"]
            _screen(cur,uid,chat_id,f"<b>{_l(language, 'payment')}</b>\n{_l(language, 'payment_off')}",[[(_l(language, 'back'),'settings')]])
        elif data=="settings:applications" and uid==admin_id:
            language=profile["language"]
            cur.execute("SELECT telegram_user_id,first_name,last_name,username FROM users WHERE state='pending' ORDER BY created_at LIMIT 20")
            pending=cur.fetchall(); blocks=[]; rows=[]
            for x in pending:
                target=x['telegram_user_id']; name=" ".join(v for v in [x['first_name'],x['last_name']] if v) or _l(language,"not_set"); username=f"@{x['username']}" if x['username'] else _l(language,"not_set")
                blocks.append(f"ID: <code>{target}</code>\nUsername: {username}\n{_l(language,'name')}: {name}")
                rows.append([(_l(language,"approve"),f"approve:{target}"),(_l(language,"reject"),f"reject:{target}")])
            rows.append([(_l(language,"back"),"settings")])
            body=f"<b>{_l(language,'requests')}</b>\n\n"+"\n\n".join(blocks) if pending else _l(language,"no_requests")
            _screen(cur,uid,chat_id,body,rows)
        elif data=="settings:access" and uid==admin_id: _access_screen(cur,uid,chat_id)
        elif data=="access:add" and uid==admin_id: _identifier_type_screen(cur,uid,chat_id,"approved")
        elif data=="access:block" and uid==admin_id: _identifier_type_screen(cur,uid,chat_id,"blocked")
        elif data.startswith("access:approved:") and uid==admin_id:
            kind=data.rsplit(":",1)[1]; cur.execute("UPDATE users SET wizard=%s::jsonb WHERE telegram_user_id=%s",(json.dumps({"await":"access_identifier","decision":"approved","kind":kind}),uid)); _screen(cur,uid,chat_id,_l(profile["language"],"send_identifier"),[[(_l(profile["language"],"cancel"),'settings:access')]])
        elif data.startswith("access:blocked:") and uid==admin_id:
            kind=data.rsplit(":",1)[1]; cur.execute("UPDATE users SET wizard=%s::jsonb WHERE telegram_user_id=%s",(json.dumps({"await":"access_identifier","decision":"blocked","kind":kind}),uid)); _screen(cur,uid,chat_id,_l(profile["language"],"send_block_identifier"),[[(_l(profile["language"],"cancel"),'settings:access')]])
        elif data.startswith("access:confirm:") and uid==admin_id:
            decision=data.rsplit(":",1)[1]
            cur.execute("SELECT wizard FROM users WHERE telegram_user_id=%s",(uid,)); pending=(cur.fetchone() or {}).get("wizard") or {}
            if pending.get("await")=="access_confirmation" and pending.get("decision")==decision:
                linked=None; displays=[]
                for item in pending.get("identifiers") or []:
                    display,item_linked=_store_access_decision(cur,uid,item["kind"],item["value"],decision)
                    displays.append(display); linked=linked or item_linked
                cur.execute("UPDATE users SET wizard='{}'::jsonb WHERE telegram_user_id=%s",(uid,))
                result=_l(profile["language"],"access_added" if decision=="approved" else "access_blocked")
                suffix=f"\nTelegram ID: <code>{linked}</code>" if linked else "\n"+_l(profile["language"],"rule_later")
                _screen(cur,uid,chat_id,f"<b>{_l(profile['language'],'access_updated')}</b>\n{escape(', '.join(displays))}: {result}.{suffix}",[[(_l(profile["language"],"back"),'settings:access')]])
        elif data.startswith("access:identify:") and uid==admin_id:
            kind=data.rsplit(":",1)[1]
            cur.execute("SELECT wizard FROM users WHERE telegram_user_id=%s",(uid,)); pending=(cur.fetchone() or {}).get("wizard") or {}
            if pending.get("await")=="identifier_kind":
                _access_confirmation(cur,uid,chat_id,[(kind,pending["raw"])])
        elif data=="access:list" and uid==admin_id:
            cur.execute("SELECT identifier_type,display_value,decision,linked_telegram_user_id FROM access_identifiers ORDER BY updated_at DESC LIMIT 30"); rules=cur.fetchall()
            language=profile["language"]
            body=f"<b>{_l(language,'rules_title')}</b>\n\n"+"\n".join(f"{x['display_value']} — {_l(language,'allowed' if x['decision']=='approved' else 'blocked')}"+(f" · <code>{x['linked_telegram_user_id']}</code>" if x['linked_telegram_user_id'] else "") for x in rules) if rules else _l(language,"rules_empty")
            _screen(cur,uid,chat_id,body,[[(_l(language,'back'),'settings:access')]])
        elif data=="filter:new":
            cur.execute("SELECT default_city_name FROM users WHERE telegram_user_id=%s",(uid,)); city=(cur.fetchone() or {}).get("default_city_name") or "Bakı"
            cur.execute("INSERT INTO filters(telegram_user_id,name,is_enabled,basic) VALUES(%s,%s,false,%s::jsonb) RETURNING id",(uid,_l(profile["language"],"new_filter"),json.dumps({"city":[city]}))); _wizard(cur,uid,chat_id,str(cur.fetchone()["id"]),"deal")
        elif data.startswith("filter:cancel:"):
            filter_id=data.rsplit(":",1)[1]
            cur.execute("UPDATE filters SET deleted_at=now(),is_enabled=false WHERE id=%s AND telegram_user_id=%s AND is_enabled=false",(filter_id,uid))
            _main(cur,uid,chat_id,profile["language"])
        elif data.startswith("filter:activate:"):
            filter_id=data.rsplit(":",1)[1]
            cur.execute("UPDATE filters SET is_enabled=true,updated_at=now() WHERE id=%s AND telegram_user_id=%s AND deleted_at IS NULL RETURNING id",(filter_id,uid))
            queued=_enqueue_today(cur,uid,filter_id) if cur.fetchone() else 0
            language=profile["language"]
            note=_l(language,"found",count=queued) if queued else _l(language,"none_today")
            _screen(cur,uid,chat_id,f"<b>{_l(language,'saved')}</b>\n{note}",[[(_l(language,"main"),"main")]])
        elif data.startswith("wf:"): _wizard_callback(cur,uid,chat_id,data)
        elif data=="filter:list":
            cur.execute("SELECT id,name,basic FROM filters WHERE telegram_user_id=%s AND deleted_at IS NULL ORDER BY created_at",(uid,)); rows=cur.fetchall()
            buttons=[[(row["name"],f"additional:{row['id']}")] for row in rows]; buttons.append([(_l(profile["language"],"back"),"main")])
            _screen(cur,uid,chat_id,f"<b>{_l(profile['language'],'filters')}</b>" if rows else _l(profile["language"],"no_filters"),buttons)
        elif data=="additional:list":
            cur.execute("SELECT id,name FROM filters WHERE telegram_user_id=%s AND deleted_at IS NULL ORDER BY created_at",(uid,)); rows=cur.fetchall()
            buttons=[[(row["name"],f"additional:{row['id']}")] for row in rows]; buttons.append([(_l(profile["language"],"back"),"main")])
            _screen(cur,uid,chat_id,_l(profile["language"],"choose_filter"),buttons)
        elif data.startswith("additional:"): _additional(cur,uid,chat_id,data.split(":",1)[1])
        elif data.startswith("ad:"):
            _,fid,field=data.split(":",2)
            if field=="seller": _seller_screen(cur,uid,chat_id,fid)
            else: _repair_screen(cur,uid,chat_id,fid)
        elif data.startswith("av:"):
            _,fid,field,value=data.split(":",3)
            if field=='seller':
                _toggle_additional(cur,fid,uid,'seller_type',value,{'owner','agency'}); _seller_screen(cur,uid,chat_id,fid)
            else:
                _toggle_additional(cur,fid,uid,'repair_status',value,{'var','yoxdur','unknown'}); _repair_screen(cur,uid,chat_id,fid)
    return {"ok": True}
