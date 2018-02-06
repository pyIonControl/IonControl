import getpass
import smtplib

data_template = "From: {}\r\nTo: {}\r\nSubject: {}\r\n\r\n{}\r\n"

class EmailNotification:
    def __init__(self, domain):
        self.server = "smtp." + domain
        self.sender = "{}@{}".format(getpass.getuser(), domain)

    def message(self, recipients, title, message, priority=None):
        if isinstance(recipients, str):
            recipients = [recipients]
        server = smtplib.SMTP(self.server)
        DATA = data_template.format(self.sender, ", ".join(recipients), title, message)
        response = server.sendmail(self.sender, recipients, DATA)
        return response