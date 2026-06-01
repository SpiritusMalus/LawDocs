"""Резолв значений полей form_data с учётом алиасов.

Поля контактов собираются wizard'ом под каноническими именами
(`full_name`, `contact_address`, `phone`, `email`), но конфиги ситуаций
ссылаются на них под историческими именами (`user_full_name`, `user_address`
и т.п.). Этот модуль — единый источник правды для сопоставления имён,
переиспользуется и в подстановке плейсхолдеров (llm.py), и в построении
шапки документа (docgen.py).
"""

# canonical-имя → все имена, под которыми поле может встретиться (вкл. canonical)
_FIELD_ALIASES: dict[str, list[str]] = {
    "full_name":       ["user_full_name", "full_name"],
    "contact_address": ["user_address", "contact_address"],
    "phone":           ["user_phone", "phone"],
    "email":           ["user_email", "email"],
    "name":            ["user_full_name", "full_name", "name"],
    "address":         ["user_address", "contact_address", "address"],
}


def resolve_field_value(name: str, form_data: dict) -> str:
    """Возвращает значение поля по имени с учётом алиасов.

    Порядок: прямое попадание по имени → поиск через группы алиасов
    (имя может быть как каноническим ключом, так и одним из его вариантов).
    Возвращает пустую строку, если значение не найдено.
    """
    direct = form_data.get(name)
    if direct:
        return str(direct)

    for canonical, variants in _FIELD_ALIASES.items():
        if name == canonical or name in variants:
            for candidate in variants:
                value = form_data.get(candidate)
                if value:
                    return str(value)
    return ""


def is_known_field(name: str, form_data: dict) -> bool:
    """True, если имя — реальный ключ form_data или известный алиас такого ключа.

    Нужно, чтобы отличить «известное поле с пустым значением» (плейсхолдер
    схлопывается в пустую строку) от неизвестного плейсхолдера (остаётся как есть).
    """
    if name in form_data:
        return True
    for canonical, variants in _FIELD_ALIASES.items():
        if name == canonical or name in variants:
            if any(candidate in form_data for candidate in variants):
                return True
    return False
