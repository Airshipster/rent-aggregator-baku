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
