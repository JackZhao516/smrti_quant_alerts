import unittest
from requests import Response

from smrti_quant_alerts.exception import error_handling


class TestException(unittest.TestCase):

    @error_handling("Test", 1, [])
    def mock_response(self, status_code: int, text: str) -> Response:
        res = Response()
        res.status_code = status_code
        bytes_string = text.encode('utf-8')
        res._content = bytes_string
        return res

    def test_exception(self) -> None:
        response = self.mock_response(200, "{}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "{}")

        response = self.mock_response(400, "{}")
        self.assertEqual(response, [])

        response = self.mock_response(400, "Bad Request")
        self.assertEqual(response, [])

        response = self.mock_response(500, "Server Error")
        self.assertEqual(response, [])
