import pytest

from notify.notification import EmailNotification

def test_email():
    notifier = EmailNotification()
    res = notifier.message(None, "Mytest", "Mymessage")
    assert res == {}
