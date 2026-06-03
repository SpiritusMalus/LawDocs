"""Сборка единых строк адреса из структурных подполей формы.

Адреса вводятся по частям (город/улица/дом/…), а в шапку документа и в генерацию
уходит одна строка. Сборка детерминированная, без внешних сервисов — ПДн никуда
не передаются. Используется для двух адресов:
  • `contact_address` — адрес заявителя (подполя `address_*`);
  • `store_address`   — адрес/сайт магазина-ответчика (подполя `store_address_*`
    + сайт `store_site`).
"""

import re

# Подполя адреса заявителя (порядок = порядок в собранной строке).
ADDRESS_SUBFIELD_IDS = (
    "address_city",
    "address_street",
    "address_house",
    "address_building",
    "address_structure",
    "address_apartment",
)

# Подполя адреса магазина (без квартиры — у магазина её нет) + отдельный сайт:
# магазин может быть онлайновым, тогда заполнен только `store_site`.
STORE_ADDRESS_SUBFIELD_IDS = (
    "store_address_city",
    "store_address_street",
    "store_address_house",
    "store_address_building",
    "store_address_structure",
)
STORE_SITE_ID = "store_site"
# Всё, что в сумме образует «адрес или сайт магазина» — для проверки «хотя бы одно».
STORE_ADDRESS_FIELD_IDS = (*STORE_ADDRESS_SUBFIELD_IDS, STORE_SITE_ID)

# Маркеры типа населённого пункта / улицы: если значение уже начинается с такого
# маркера, повторный префикс не добавляем (иначе «г. г. Москва» / «ул. пер. …»).
_CITY_MARKERS = re.compile(
    r"^(г\.|г\s|город|пос\.|пгт|с\.|село|д\.|дер\.|ст-ца|рп\.)",
    re.IGNORECASE,
)
_STREET_MARKERS = re.compile(
    r"^(ул\.|улица|пер\.|переулок|пр-кт|просп\.|проспект|пл\.|площадь|б-р|бул\.|бульвар|"
    r"наб\.|набережная|ш\.|шоссе|проезд|туп\.|тупик|аллея|линия|кв-л|квартал|мкр)",
    re.IGNORECASE,
)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _compose_physical(
    city: str,
    street: str,
    house: str,
    building: str,
    structure: str,
    apartment: str = "",
) -> str:
    """«г. Москва, ул. Пушкина, д. 1, корп. 2, стр. 3, кв. 5» — пустые части пропускаются."""
    parts: list[str] = []
    if city:
        parts.append(city if _CITY_MARKERS.match(city) else f"г. {city}")
    if street:
        parts.append(street if _STREET_MARKERS.match(street) else f"ул. {street}")
    if house:
        parts.append(f"д. {house}")
    if building:
        parts.append(f"корп. {building}")
    if structure:
        parts.append(f"стр. {structure}")
    if apartment:
        parts.append(f"кв. {apartment}")
    return ", ".join(parts)


def compose_contact_address(form_data: dict) -> str:
    """Адрес заявителя из подполей `address_*`.

    Если структурных полей нет совсем — возвращает уже имеющийся `contact_address`
    (обратная совместимость со старой формой одним полем и со старыми заказами).
    """
    if not any(_clean(form_data.get(fid)) for fid in ADDRESS_SUBFIELD_IDS):
        return _clean(form_data.get("contact_address"))

    return _compose_physical(
        city=_clean(form_data.get("address_city")),
        street=_clean(form_data.get("address_street")),
        house=_clean(form_data.get("address_house")),
        building=_clean(form_data.get("address_building")),
        structure=_clean(form_data.get("address_structure")),
        apartment=_clean(form_data.get("address_apartment")),
    )


def compose_store_address(form_data: dict) -> str:
    """Адрес и/или сайт магазина из подполей `store_address_*` + `store_site`.

    Форматы: «г. Москва, ул. …, д. 1», «www.shop.ru», либо оба через «, сайт: …».
    Если структурных полей нет совсем — возвращает уже имеющийся `store_address`
    (обратная совместимость со старой формой одним полем и со старыми заказами).
    """
    if not any(_clean(form_data.get(fid)) for fid in STORE_ADDRESS_FIELD_IDS):
        return _clean(form_data.get("store_address"))

    physical = _compose_physical(
        city=_clean(form_data.get("store_address_city")),
        street=_clean(form_data.get("store_address_street")),
        house=_clean(form_data.get("store_address_house")),
        building=_clean(form_data.get("store_address_building")),
        structure=_clean(form_data.get("store_address_structure")),
    )
    site = _clean(form_data.get(STORE_SITE_ID))

    if physical and site:
        return f"{physical}, сайт: {site}"
    return physical or site
