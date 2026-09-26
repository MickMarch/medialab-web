from slowapi import Limiter
from slowapi.util import get_remote_address

from medialab_web.constants import LOGIN_RATE_LIMIT

limiter = Limiter(key_func=get_remote_address)

__all__ = ["LOGIN_RATE_LIMIT", "limiter"]
