from typing import Any


class ClientError(Exception):
    def __init__(
        self,
        status_code: int | None,
        error_code: int | None,
        error_message: str | None,
        header: Any | None,
        error_data: Any | None = None,
    ) -> None:
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

    def __str__(self) -> str:
        return (
            f"ClientError: status code: {self.status_code}, "
            f"error code: {self.error_code}, "
            f"server error message: {self.error_message}"
        )


class ServerError(Exception):
    def __init__(self, status_code: int | None, message: str | None) -> None:
        self.status_code = status_code
        self.message = message

    def __str__(self) -> str:
        return f"ServerError: status code: {self.status_code}, server error message: {self.message}"
