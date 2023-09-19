import logging
import random
import time
from requests.exceptions import RequestException
from requests.models import Response
import json
from json import JSONDecodeError


def error_handling(api="binance", retry=5, default_val=None):
    """
    decorator for handling api request exceptions
    if a library function has direct api request, use this decorator

    if Response object is returned, check status code and raise exception if necessary
    else return the object, and use general try-except to handle exceptions

    :param api: api name: "binance", "telegram", "coingecko"
    :param retry: retry times
    :param default_val: default value to return if all retries failed
    """
    def decorator(fun):
        def wrapper(*args, **kwargs):
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
                    logging.error(f"{error_msg}: {e}")
                except Exception as e:
                    logging.error(f"{error_msg}: {e}")
                time.sleep(random.random() * 2)
            return default_val
        return wrapper
    return decorator


class ClientError(Exception):
    def __init__(self, status_code, error_code, error_message, header, error_data=None):
        # https status code
        self.status_code = status_code
        # error code returned from server
        self.error_code = error_code
        # error message returned from server
        self.error_message = error_message
        # the whole response header returned from server
        self.header = header
        # return data if it's returned from server
        self.error_data = error_data

    def __str__(self):
        return f"ClientError: status code: {self.status_code}, " \
               f"error code: {self.error_code}, " \
               f"server error message: {self.error_message}"


class ServerError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message

    def __str__(self):
        return f"ServerError: status code: {self.status_code}, " \
               f"server error message: {self.message}"
