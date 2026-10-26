import logging
import random
import time
import json
import functools
from json import JSONDecodeError
from typing import Any
from collections.abc import Callable

from requests.exceptions import RequestException
from requests.models import Response

from .error_type import ClientError, ServerError


def error_handling(api: str = "binance", retry: int = 5, default_val: Any | None = None) -> Callable:
    """
    decorator for handling api request exceptions
    if a library function has direct api request, use this decorator

    if Response object is returned, check status code and raise exception if necessary
    else return the object, and use general try-except to handle exceptions

    :param api: api name: "binance", "telegram", "coingecko"
    :param retry: retry times
    :param default_val: default value to return if all retries failed
    """

    def decorator(fun: Callable) -> Callable:
        @functools.wraps(fun)
        def wrapper(*args: Any | None, **kwargs: Any | None) -> Response | Any:
            error_msg = f"{api} api request error: {fun.__name__}"
            for i in range(retry):
                try:
                    response = fun(*args, **kwargs)
                    if isinstance(response, Response):
                        status_code = response.status_code
                        if status_code < 400:
                            return response

                        if 400 <= status_code < 500:
                            try:
                                err = json.loads(response.text)
                            except JSONDecodeError:
                                raise ClientError(status_code, None, response.text, response.headers, None) from None

                            # error code and message returned from server
                            # binance error json
                            data = err.get("data", None)
                            code = err.get("code", None)
                            msg = err.get("msg", None)

                            # telegram error json
                            code = err.get("error_code", code)
                            msg = err.get("description", msg)

                            # coingecko error json
                            msg = err.get("error", msg)

                            raise ClientError(status_code, code, msg, response.headers, data)
                        raise ServerError(status_code, response.text)
                    else:
                        return response

                except (RequestException, ClientError, ServerError) as e:
                    logging.error(f"{error_msg}: {e}, retrying {i + 1} times")
                except Exception as e:
                    logging.error(f"{error_msg}: {e}, retrying {i + 1} times")
                time.sleep(random.random() * 2)
            return default_val

        return wrapper

    return decorator
