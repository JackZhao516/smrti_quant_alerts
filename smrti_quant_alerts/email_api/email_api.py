import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Iterable

from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.exception import error_handling


class EmailApi:
    email_tokens = Config().TOKENS["GMAIL"]

    def __init__(self, sender_email: str = None, receiver_email: str = None, password: str = None) -> None:
        self.port = 465  # For SSL
        self.smtp_server = "smtp.gmail.com"
        self.sender_email = self.email_tokens["SENDER_EMAIL"] if not sender_email else sender_email
        self.receiver_email = self.email_tokens["RECEIVER_EMAIL"] if not receiver_email else receiver_email
        self.password = self.email_tokens["PASSWORD"] if not password else password

    @error_handling("email", default_val=None)
    def send_email(self, subject: str, body: str, csv_file_name: str = None,
                   pdf_file_name: Iterable[str] = None) -> None:
        """
        send email with message and csv file

        :param subject: email subject
        :param body: email body
        :param csv_file_name: csv file path
        :param pdf_file_name: pdf file path
        """
        if not self.sender_email or not self.receiver_email or not self.password:
            return

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.sender_email
        message["To"] = self.receiver_email
        message.attach(MIMEText(body, "plain"))

        if csv_file_name:
            with open(csv_file_name, encoding="utf-8") as fp:
                attachment = MIMEText(fp.read(), _subtype="text/csv")
            attachment.add_header("Content-Disposition", "attachment", filename=csv_file_name)
            message.attach(attachment)

        if pdf_file_name:
            for file_name in pdf_file_name:
                with open(file_name, "rb") as fp:
                    attachment = MIMEApplication(fp.read(), _subtype="pdf")
                attachment.add_header("Content-Disposition", "attachment", filename=file_name)
                message.attach(attachment)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.smtp_server, self.port, context=context) as server:
            server.login(self.sender_email, self.password)
            server.sendmail(self.sender_email, self.receiver_email, message.as_string())
