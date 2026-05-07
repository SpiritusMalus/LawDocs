from slowapi import Limiter
from slowapi.util import get_remote_address

# Единственный экземпляр — все роутеры используют его,
# чтобы лимиты работали в общем счётчике, а не по-роутерно.
limiter = Limiter(key_func=get_remote_address)
