from enum import Enum


class OrderStatus(str, Enum):
    """Статусы заказа.

    Жизненный цикл (генерация ДО оплаты): DRAFT → GENERATING → PREVIEW_READY
    → PENDING_PAYMENT → PAID → DONE | FAILED | REFUNDED.
    PREVIEW_READY — документ уже сгенерирован, показываем watermarked-превью,
    но скачать чистый файл нельзя до оплаты.

    Наследование от str: значения сериализуются и сравниваются как обычные
    строки, поэтому колонка в БД остаётся String и миграция не нужна.
    """

    DRAFT = "draft"
    GENERATING = "generating"
    PREVIEW_READY = "preview_ready"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    DONE = "done"
    FAILED = "failed"
    REFUNDED = "refunded"
