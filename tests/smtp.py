SERVER = "smtp.sandia.gov"
FROM = "plmaunz@sandia.gov"
TO = ["peter.maunz@gmail.com"] # must be a list

SUBJECT = "Hello!"
TEXT = "This is a test #2 of emailing through smtp. Troubleshooting for a ticket."

# Prepare actual message
message = """From: %s\r\nTo: %s\r\nSubject: %s\r\n\

%s
""" % (FROM, ", ".join(TO), SUBJECT, TEXT)

# Send the mail
import smtplib
server = smtplib.SMTP(SERVER)
response = server.sendmail(FROM, TO, message)
server.quit()
print(response)