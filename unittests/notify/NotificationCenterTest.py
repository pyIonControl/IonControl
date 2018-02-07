import datetime
import pytest

from notify.notification import NotificationCenter, NotificationSubscription

def test_center():
    nc = NotificationCenter()
    nc.subscriptions.append(NotificationSubscription(name="subscription", recipients=None,
                                                     subscriptions=set(["test"]), enabled=True))
    num = nc.notify("test", "NotificationCenter", "Everything is okay, this is just a test")
    assert num == 1


def test_center_rate():
    nc = NotificationCenter()
    nc.subscriptions.append(NotificationSubscription(name="subscription", recipients=None,
                                                     subscriptions=set(["test"]), enabled=True))
    num = nc.notify("test", "NotificationCenter", "Everything is okay, this is just a test 1")
    num = nc.notify("test", "NotificationCenter", "Everything is okay, this is just a test 2")
    num = nc.notify("test", "NotificationCenter", "Everything is okay, this is just a test 3")
    num = nc.notify("test", "NotificationCenter", "Everything is okay, this is just a test 4")
    num = nc.notify("test", "NotificationCenter", "Everything is okay, this is just a test 5")
    num = nc.notify("test", "NotificationCenter", "Everything is okay, this is just a test 6")
    assert num == 1

    nc.periodicWork(minDelay=datetime.timedelta())