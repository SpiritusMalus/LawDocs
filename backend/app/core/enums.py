from enum import Enum


class OrderStatus(str, Enum):
    """Статусы заказа.

    Жизненный цикл: DRAFT → PENDING_PAYMENT → GENERATING → DONE | FAILED | REFUNDED.

    Наследование от str: значения сериализуются и сравниваются как обычные
    строки, поэтому колонка в БД остаётся String и миграция не нужна.
    """

    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    GENERATING = "generating"
    DONE = "done"
    FAILED = "failed"
    REFUNDED = "refunded"
