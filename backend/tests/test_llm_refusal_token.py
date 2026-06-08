"""Тесты L3/L4: детект отказа модели и свежесть токена GigaChat."""

from datetime import UTC, datetime, timedelta

from app.services.llm import _REFUSAL_MARKERS, _is_gigachat_refusal


def test_detects_known_refusals():
    refusals = [
        "Извините, как языковая модель, я не могу помочь с этим.",
        "Я не юрист и не могу дать юридическую консультацию.",
        "Не могу обсуждать чувствительные темы.",
        "Как искусственный интеллект, я не уполномочен составлять такие документы.",
    ]
    for text in refusals:
        assert _is_gigachat_refusal(text), text


def test_does_not_flag_normal_legal_narrative():
    legit = (
        "15 марта 2025 года я приобрёл холодильник, который через неделю перестал "
        "морозить. Магазин отказался вернуть деньги. Прошу расторгнуть договор и "
        "вернуть уплаченную сумму в полном объёме."
    )
    assert not _is_gigachat_refusal(legit)


def test_markers_are_lowercase_for_case_insensitive_match():
    # _is_gigachat_refusal приводит вход к lower(); маркеры тоже должны быть lower,
    # иначе сравнение никогда не сmatchится.
    assert all(m == m.lower() for m in _REFUSAL_MARKERS)


class _FakeProvider:
    """Минимальный носитель состояния токена для проверки _token_is_fresh."""

    from app.services.llm import GigaChatProvider

    _token_is_fresh = GigaChatProvider._token_is_fresh

    def __init__(self, token, expires_at):
        self._token = token
        self._token_expires_at = expires_at


def test_token_fresh_logic():
    now = datetime.now(UTC)
    assert _FakeProvider("t", now + timedelta(minutes=10))._token_is_fresh() is True
    # Истекает в пределах skew-окна (60 с) → считаем несвежим.
    assert _FakeProvider("t", now + timedelta(seconds=30))._token_is_fresh() is False
    assert _FakeProvider("t", now - timedelta(minutes=1))._token_is_fresh() is False
    assert _FakeProvider(None, now + timedelta(minutes=10))._token_is_fresh() is False
