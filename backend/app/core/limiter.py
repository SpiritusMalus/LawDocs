from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _get_real_ip(request: Request) -> str:
    # Cloudflare устанавливает CF-Connecting-IP с реальным IP пользователя.
    # Это надёжнее X-Forwarded-For, который можно подделать до Cloudflare.
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    # Nginx устанавливает X-Real-IP ($remote_addr)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    # X-Forwarded-For: первый адрес — оригинальный клиент
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Единственный экземпляр — все роутеры используют его,
# чтобы лимиты работали в общем счётчике, а не по-роутерно.
limiter = Limiter(key_func=_get_real_ip)
