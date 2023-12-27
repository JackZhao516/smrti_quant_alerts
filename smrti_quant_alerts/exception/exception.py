import logging
import random
import time
import json
from json import JSONDecodeError
from typing import Callable, Optional, Union, Any

from requests.exceptions import RequestException
from requests.models import Response

from .error_type import ClientError, ServerError


def error_handling(api: str = "binance", retry: int = 5, default_val: Optional[Any] = None) -> Callable:
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
        def wrapper(*args: Optional[Any], **kwargs: Optional[Any]) -> Union[Response, Any]:
            error_msg = f"{api} api request error: {fun.__name__}"
            for i in range(retry):
                try:
                    response = fun(*args, **kwargs)
                    if type(response) == Response:
                        status_code = response.status_code
                        if status_code < 400:
                            return response

                        if 400 <= status_code < 500:
                            try:
                                err = json.loads(response.text)
                            except JSONDecodeError:
                                raise ClientError(
                                    status_code, None, response.text, None, response.headers
                                )

                            # error code and message returned from server
                            # binance error json
                            data = err["data"] if "data" in err else None
                            code = err["code"] if "code" in err else None
                            msg = err["msg"] if "msg" in err else None

                            # telegram error json
                            code = err["error_code"] if "error_code" in err else code
                            msg = err["description"] if "description" in err else msg

                            # coingecko error json
                            msg = err["error"] if "error" in err else msg

                            raise ClientError(
                                status_code, code, msg, response.headers, data
                            )
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
