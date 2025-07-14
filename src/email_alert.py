import smtplib
from email.mime.text import MIMEText

class EmailAlert:
    def __init__(self, smtp_server, smtp_port, user, password, to_email):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.user = user
        self.password = password
        self.to_email = to_email

    def send(self, subject, body):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.user
        msg['To'] = self.to_email

        with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
            server.login(self.user, self.password)
            server.sendmail(self.user, self.to_email, msg.as_string())