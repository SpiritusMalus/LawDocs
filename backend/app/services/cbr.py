"""Получение ключевой ставки ЦБ РФ через SOAP API cbr.ru."""
import logging
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from decimal import Decimal

import httpx

logger = logging.getLogger(__name__)

_CBR_SOAP_URL = "https://cbr.ru/DailyInfoWebServ/DailyInfo.asmx"
_SOAP_BODY = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"'
    ' xmlns:web="http://web.cbr.ru/">'
    "<soap:Body>"
    "<web:KeyRate>"
    "<web:fromDate>{from_date}</web:fromDate>"
    "<web:ToDate>{to_date}</web:ToDate>"
    "</web:KeyRate>"
    "</soap:Body>"
    "</soap:Envelope>"
)


async def fetch_cb_rate() -> Decimal | None:
    """Возвращает текущую ключевую ставку ЦБ РФ или None при ошибке."""
    today = date.today()
    from_date = today - timedelta(days=14)
    body = _SOAP_BODY.format(
        from_date=from_date.strftime("%Y-%m-%dT00:00:00"),
        to_date=today.strftime("%Y-%m-%dT00:00:00"),
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _CBR_SOAP_URL,
                content=body.encode("utf-8"),
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://web.cbr.ru/KeyRate",
                },
            )
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        rates = root.findall(".//{http://web.cbr.ru/}Rate")
        if not rates:
            logger.error("cbr_rate_parse_failed: no Rate elements in response")
            return None

        last_rate = rates[-1].text
        if not last_rate:
            logger.error("cbr_rate_parse_failed: Rate element is empty")
            return None

        return Decimal(last_rate.replace(",", "."))
    except Exception as e:
        logger.error("cbr_rate_fetch_failed: %s: %s", type(e).__name__, str(e))
        return None
