from __future__ import annotations


# Canonical source names are kept as identifiers. Baku is intentionally first in UI.
CITIES = [
    (1, "Bakı"), (2, "Gəncə"), (3, "Sumqayıt"), (34, "Xırdalan"),
    (85, "Ağcabədi"), (84, "Ağdam"), (23, "Ağdaş"), (90, "Ağdərə"),
    (30, "Ağstafa"), (75, "Ağsu"), (11, "Astara"), (76, "Balakən"),
    (17, "Beyləqan"), (18, "Bərdə"), (13, "Biləsuvar"), (92, "Cəbrayıl"),
    (9, "Cəlilabad"), (89, "Daşkəsən"), (86, "Füzuli"), (83, "Gədəbəy"),
    (74, "Goranboy"), (22, "Göyçay"), (87, "Göygöl"), (12, "Göytəpə"),
    (35, "Hacıqabul"), (26, "Xaçmaz"), (98, "Xankəndi"), (41, "Xızı"),
    (100, "Xocalı"), (99, "Xocavənd"), (31, "Xudat"), (10, "İmişli"),
    (38, "İsmayıllı"), (94, "Kəlbəcər"), (77, "Kürdəmir"), (33, "Qax"),
    (79, "Qazax"), (39, "Qəbələ"), (129, "Qobustan"), (24, "Quba"),
    (95, "Qubadlı"), (25, "Qusar"), (96, "Laçın"), (82, "Lerik"),
    (8, "Lənkəran"), (37, "Masallı"), (20, "Mingəçevir"), (81, "Naftalan"),
    (130, "Naxçıvan"), (80, "Naxçıvan MR"), (7, "Neftçala"), (36, "Oğuz"),
    (14, "Saatlı"), (15, "Sabirabad"), (6, "Salyan"), (97, "Samux"),
    (27, "Siyəzən"), (28, "Şabran"), (16, "Şamaxı"), (19, "Şəki"),
    (4, "Şəmkir"), (5, "Şirvan"), (101, "Şuşa"), (88, "Tərtər"),
    (29, "Tovuz"), (78, "Ucar"), (102, "Yardımlı"), (21, "Yevlax"),
    (32, "Zaqatala"), (93, "Zəngilan"), (40, "Zərdab"),
]

BAKU_REGIONS = [
    (197, "Abşeron"), (58, "Binəqədi"), (16, "Xətai"), (15, "Xəzər"),
    (57, "Qaradağ"), (10, "Nərimanov"), (190, "Nəsimi"), (11, "Nizami"),
    (249, "Pirallahı"), (13, "Sabunçu"), (12, "Səbail"), (14, "Suraxanı"),
    (56, "Yasamal"),
]

CITY_BY_ID = dict(CITIES)

RU_CITY_NAMES = {
    1:"Баку",2:"Гянджа",3:"Сумгаит",34:"Хырдалан",85:"Агджабеди",84:"Агдам",23:"Агдаш",90:"Агдере",
    30:"Агстафа",75:"Агсу",11:"Астара",76:"Балекен",17:"Бейлаган",18:"Барда",13:"Билясувар",92:"Джебраил",
    9:"Джалилабад",89:"Дашкесан",86:"Физули",83:"Гедабек",74:"Геранбой",22:"Гёйчай",87:"Гёйгёль",12:"Гёйтепе",
    35:"Аджикабул",26:"Хачмаз",98:"Ханкенди",41:"Хызы",100:"Ходжалы",99:"Ходжавенд",31:"Худат",10:"Имишли",
    38:"Исмаиллы",94:"Кельбаджар",77:"Кюрдамир",33:"Гах",79:"Газах",39:"Габала",129:"Гобустан",24:"Губа",
    95:"Губадлы",25:"Гусар",96:"Лачин",82:"Лерик",8:"Ленкоран",37:"Масаллы",20:"Мингячевир",81:"Нафталан",
    130:"Нахчыван",80:"Нахчыванская АР",7:"Нефтчала",36:"Огуз",14:"Саатлы",15:"Сабирабад",6:"Сальян",97:"Самух",
    27:"Сиазань",28:"Шабран",16:"Шамахы",19:"Шеки",4:"Шамкир",5:"Ширван",101:"Шуша",88:"Тертер",
    29:"Товуз",78:"Уджар",102:"Ярдымлы",21:"Евлах",32:"Закаталы",93:"Зангилан",40:"Зардаб",
}

EN_CITY_NAMES = {
    1:"Baku",2:"Ganja",3:"Sumgayit",34:"Khirdalan",85:"Agjabadi",84:"Aghdam",23:"Agdash",90:"Aghdara",
    30:"Aghstafa",75:"Aghsu",11:"Astara",76:"Balakan",17:"Beylagan",18:"Barda",13:"Bilasuvar",92:"Jabrayil",
    9:"Jalilabad",89:"Dashkasan",86:"Fuzuli",83:"Gadabay",74:"Goranboy",22:"Goychay",87:"Goygol",12:"Goytapa",
    35:"Hajigabul",26:"Khachmaz",98:"Khankendi",41:"Khizi",100:"Khojaly",99:"Khojavend",31:"Khudat",10:"Imishli",
    38:"Ismayilli",94:"Kalbajar",77:"Kurdamir",33:"Gakh",79:"Gazakh",39:"Gabala",129:"Gobustan",24:"Guba",
    95:"Gubadli",25:"Gusar",96:"Lachin",82:"Lerik",8:"Lankaran",37:"Masalli",20:"Mingachevir",81:"Naftalan",
    130:"Nakhchivan",80:"Nakhchivan AR",7:"Neftchala",36:"Oghuz",14:"Saatli",15:"Sabirabad",6:"Salyan",97:"Samukh",
    27:"Siyazan",28:"Shabran",16:"Shamakhi",19:"Shaki",4:"Shamkir",5:"Shirvan",101:"Shusha",88:"Tartar",
    29:"Tovuz",78:"Ujar",102:"Yardimli",21:"Yevlakh",32:"Zagatala",93:"Zangilan",40:"Zardab",
}


def city_label(city_id: int, language: str) -> str:
    if language == "ru":
        return RU_CITY_NAMES.get(city_id, CITY_BY_ID[city_id])
    if language == "en":
        return EN_CITY_NAMES.get(city_id, CITY_BY_ID[city_id])
    return CITY_BY_ID[city_id]
