TEXT = {
 "ru": {"closed":"Бот работает по закрытому доступу.","apply":"Отправить заявку","sent":"Заявка отправлена администратору.","menu":"Настроить фильтр|Мои фильтры|Дополнительные условия|Настройки","language":"Выберите язык","approved":"Доступ одобрен. Настройте фильтр.","warning":"Необязательные поля авторы часто не заполняют. При строгом условии объявления без явно указанного значения не попадут в уведомления."},
 "az": {"closed":"Bot qapalı girişlə işləyir.","apply":"Müraciət göndər","sent":"Müraciət administratora göndərildi.","menu":"Filtri tənzimlə|Filtrlərim|Əlavə şərtlər|Ayarlar","language":"Dili seçin","approved":"Giriş təsdiqləndi. Filtri tənzimləyin.","warning":"Müəlliflər əlavə sahələri çox vaxt doldurmurlar. Sərt şərt seçilərsə, açıq göstərilməyən elanlar gəlməyəcək."},
 "en": {"closed":"This bot has closed access.","apply":"Request access","sent":"Your request was sent to the administrator.","menu":"Configure filter|My filters|Additional conditions|Settings","language":"Choose language","approved":"Access approved. Configure your filter.","warning":"Authors often omit optional fields. A strict condition excludes listings where that value is not explicitly stated."}
}


def t(language: str, key: str) -> str:
    return TEXT.get(language, TEXT["ru"])[key]
