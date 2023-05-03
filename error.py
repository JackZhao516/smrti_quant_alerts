import json
from json import JSONDecodeError


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


class ServerError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message


def handle_exception(response):
    status_code = response.status_code
    if status_code < 400:
        return
    if 400 <= status_code < 500:
        try:
            err = json.loads(response.text)
        except JSONDecodeError:
            raise ClientError(
                status_code, None, response.text, None, response.headers
            )

        data = err["data"] if "data" in err else None
        code = err["code"] if "code" in err else None
        msg = err["msg"] if "msg" in err else None
        raise ClientError(
            status_code, code, msg, response.headers, data
        )
    raise ServerError(status_code, response.text)
