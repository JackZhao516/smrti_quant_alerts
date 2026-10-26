import os
import tempfile
import unittest
from unittest import mock

from smrti_quant_alerts.email_api import EmailApi


class TestEmailApi(unittest.TestCase):
    def setUp(self) -> None:
        self.email_api = EmailApi(
            sender_email="sender@example.com", receiver_email=["receiver@example.com"], password="password"
        )

    def test_send_email_without_credentials(self) -> None:
        self.email_api.sender_email = ""
        with mock.patch("smtplib.SMTP_SSL") as mock_smtp:
            self.email_api.send_email("subject", "body")
        mock_smtp.assert_not_called()

    def test_send_email_with_attachments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = os.path.join(temp_dir, "test.csv")
            pdf_file = os.path.join(temp_dir, "test.pdf")
            with open(csv_file, "w", encoding="utf-8") as file:
                file.write("test1,test2\n")
            with open(pdf_file, "wb") as file:
                file.write(b"test")

            with (
                mock.patch("smtplib.SMTP_SSL") as mock_smtp,
                mock.patch("ssl.create_default_context") as mock_create_default_context,
            ):
                server = mock_smtp.return_value.__enter__.return_value
                self.email_api.send_email("subject", "<p>body</p>", [csv_file], [pdf_file], user_html=True)

            mock_create_default_context.assert_called_once_with()
            mock_smtp.assert_called_once_with("smtp.gmail.com", 465, context=mock_create_default_context.return_value)
            server.login.assert_called_once_with("sender@example.com", "password")
            server.sendmail.assert_called_once()
            self.assertEqual(server.sendmail.call_args[0][0], "sender@example.com")
            self.assertEqual(server.sendmail.call_args[0][1], ["receiver@example.com"])
