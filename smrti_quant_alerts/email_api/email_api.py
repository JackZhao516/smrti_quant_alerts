import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Iterable, List

from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.exception import error_handling


class EmailApi:
    email_tokens = Config().TOKENS["GMAIL"]

    def __init__(self, sender_email: str = None, receiver_email: str = None, password: str = None) -> None:
        self.port = 465  # For SSL
        self.smtp_server = "smtp.gmail.com"
        self.sender_email = self.email_tokens["SENDER_EMAIL"] if not sender_email else sender_email
        self.receiver_emails = self.email_tokens["RECEIVER_EMAIL"] if not receiver_email else receiver_email
        self.password = self.email_tokens["PASSWORD"] if not password else password

    @error_handling("email", default_val=None)
    def send_email(self, subject: str, body: str, csv_file_names: List[str] = None,
                   pdf_or_xlsx_file_names: Iterable[str] = None) -> None:
        """
        send email with message and csv file

        :param subject: email subject
        :param body: email body
        :param csv_file_names: list of csv file path
        :param pdf_or_xlsx_file_names: pdf or xlsx file path
        """
        if not self.sender_email or not self.receiver_emails or not self.password:
            return

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.sender_email
        message["To"] = ','.join(self.receiver_emails)
        message.attach(MIMEText(body, "plain"))

        if csv_file_names:
            for csv_file_name in csv_file_names:
                with open(csv_file_name, encoding="utf-8") as fp:
                    attachment = MIMEText(fp.read(), _subtype="text/csv")
                attachment.add_header("Content-Disposition", "attachment", filename=csv_file_name)
                message.attach(attachment)

        if pdf_or_xlsx_file_names:
            for file_name in pdf_or_xlsx_file_names:
                with open(file_name, "rb") as fp:
                    attachment = MIMEApplication(fp.read(), _subtype="pdf")
                attachment.add_header("Content-Disposition", "attachment", filename=file_name)
                message.attach(attachment)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.smtp_server, self.port, context=context) as server:
            server.login(self.sender_email, self.password)
            server.sendmail(self.sender_email, self.receiver_emails, message.as_string())
