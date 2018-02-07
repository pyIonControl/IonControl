import pytest

from notification.email import EmailNotification

def test_email():
    notifier = EmailNotification("sandia.gov")
    res = notifier.message(["jo4drhy2xe@pomail.net"], "Mytest", "Mymessage")
    assert res == {}
