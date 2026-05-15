import ipaddress

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _is_trusted_proxy(host: str) -> bool:
    # Доверяем заголовкам только если запрос пришёл с приватного IP (nginx/Docker).
    # Публичный IP не может установить CF-Connecting-IP или X-Real-IP легитимно.
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False


def _get_real_ip(request: Request) -> str:
    client_host = request.client.host if request.client else ""
    if _is_trusted_proxy(client_host):
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Единственный экземпляр — все роутеры используют его,
# чтобы лимиты работали в общем счётчике, а не по-роутерно.
limiter = Limiter(key_func=_get_real_ip)
