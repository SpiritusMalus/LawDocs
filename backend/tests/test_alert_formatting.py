"""Регресс-тесты текста алертов мониторинга (system-design §4)."""

from app.services.notifications import (
    format_refund_spike_alert,
    format_stuck_orders_alert,
)


def test_stuck_orders_alert_lists_every_order():
    msg = format_stuck_orders_alert(
        [("abc-1", "paid", "ddu_delay"), ("def-2", "generating", "employer")],
        120,
    )
    assert "Stuck PAID orders" in msg
    assert "> 120 мин" in msg
    assert "<code>abc-1</code>" in msg and "[paid]" in msg and "ddu_delay" in msg
    assert "<code>def-2</code>" in msg and "[generating]" in msg


def test_refund_spike_alert_reports_delta():
    msg = format_refund_spike_alert(4, 15)
    assert "Refund spike" in msg
    assert "4" in msg and "15" in msg
