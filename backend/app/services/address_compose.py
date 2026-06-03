"""Сборка единой строки адреса из структурных подполей формы.

Пользователь вводит адрес по частям (город/улица/дом/корпус/строение/квартира),
а в шапку документа и в генерацию уходит одна строка `contact_address`. Сборка
детерминированная, без внешних сервисов — ПДн никуда не передаются.
"""

import re

# Подполя структурного адреса (порядок = порядок в собранной строке).
ADDRESS_SUBFIELD_IDS = (
    "address_city",
    "address_street",
    "address_house",
    "address_building",
    "address_structure",
    "address_apartment",
)

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


def compose_contact_address(form_data: dict) -> str:
    """«г. Москва, ул. Пушкина, д. 1, корп. 2, стр. 3, кв. 5» из подполей.

    Пустые части пропускаются. Если структурных полей нет совсем — возвращает
    уже имеющийся `contact_address` (обратная совместимость со старой формой
    одним полем и со старыми заказами).
    """
    city = _clean(form_data.get("address_city"))
    street = _clean(form_data.get("address_street"))
    house = _clean(form_data.get("address_house"))
    building = _clean(form_data.get("address_building"))
    structure = _clean(form_data.get("address_structure"))
    apartment = _clean(form_data.get("address_apartment"))

    if not any(_clean(form_data.get(fid)) for fid in ADDRESS_SUBFIELD_IDS):
        return _clean(form_data.get("contact_address"))

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
