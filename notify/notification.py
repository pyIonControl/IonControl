import getpass
import logging
import smtplib
import socket

from datetime import datetime, timedelta, timezone
from collections import namedtuple

data_template = "From: {}\r\nTo: {}\r\nSubject: {}\r\n\r\n{}\r\n"

MessageData = namedtuple("MessageData", "title, message, timestamp")

class EmailNotification:
    def __init__(self, domain=None):
        self.domain = domain or ".".join(socket.getfqdn().split(".")[-2:])
        self.server = "smtp." + self.domain
        self.sender = "{}@{}".format(getpass.getuser(), self.domain)

    def message(self, recipients, title, message):
        if recipients is None:
            recipients = [self.sender]
        if isinstance(recipients, str):
            recipients = [recipients]
        server = smtplib.SMTP(self.server)
        DATA = data_template.format(self.sender, ", ".join(recipients), title, message)
        response = server.sendmail(self.sender, recipients, DATA)
        return response


class NotificationSubscription:
    def __init__(self, name=None, recipients=None, subscriptions=set(), enabled=False):
        self.enabled = enabled
        self.name = name
        self.recipients = recipients
        self.subscriptions = subscriptions
        self.lastSent = datetime.fromtimestamp(0, timezone.utc)
        self.pendingMessages = list()


class NotificationCenter:
    def __init__(self, subscriptions=None, notifyer=EmailNotification()):
        self.subscriptions = subscriptions if subscriptions is not None else list()
        self.origins = set()
        self.notifyer = notifyer

    def register(self, origin):
        if isinstance(origin, str):
            self.origins.add(origin)
        else:
            self.origins.update(set(origin))

    def notify(self, origin, title=None, message=None, priority=None):
        self.origins.add(origin)
        matching_subscriptions = 0
        if message:
            for s in self.subscriptions:
                if s.enabled and origin in s.subscriptions:
                    s.pendingMessages.append(MessageData(title or origin, message, datetime.now(timezone.utc)))
                    self._sendRateLimited(s)
                    matching_subscriptions += 1
            if matching_subscriptions == 0:
                logging.getLogger(__name__).info("No recipients for origin: {} title: {} message: {}".format(origin, title, message))
        return matching_subscriptions

    def _sendRateLimited(self, subscription, minDelay=None):
        if minDelay is None:
            minDelay = timedelta(minutes=15)
        if subscription.pendingMessages:
            now = datetime.now(timezone.utc)
            if now - subscription.lastSent >= minDelay:
                self._send(subscription)

    def periodicWork(self, minDelay=None):
        for s in self.subscriptions:
            self._sendRateLimited(s, minDelay)

    def _send(self, subscription):
        if subscription.pendingMessages:
            combined = "\r\n".join("{:%Y-%m-%d %H:%M:%S%z} {}: {}".format(m.timestamp.astimezone(), m.title, m.message) for m in subscription.pendingMessages)
            self.notifyer.message(subscription.recipients, subscription.pendingMessages[-1].title, combined)
            subscription.pendingMessages.clear()
            subscription.lastSent = datetime.now(timezone.utc)
