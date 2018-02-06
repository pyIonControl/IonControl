import pytest

from notification.email import EmailNotification

def test_email():
    notifier = EmailNotification("sandia.gov")
    res = notifier.message("peter@maunz.us", "Mytest", "Mymessage")
    assert res == {}
