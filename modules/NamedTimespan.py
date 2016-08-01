# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from datetime import datetime, time, timedelta
import pytz

def now():
    return datetime.utcnow().replace(tzinfo= pytz.utc )



timespans = ['last 15 min', 'last 30 min', 'last hour', 'last 2 hours', 'last 6 hours', 'Today', 'One day', 'Three days', 'One week', 'One month', 'Three month', 'One year', 'All', 'Custom']

lookup = { 'last 15 min': lambda now: now - timedelta(seconds=15*60),
           'last 30 min': lambda now: now - timedelta(seconds=30*60), 
           'last hour':   lambda now: now - timedelta(hours=1), 
           'last 2 hours':   lambda now: now - timedelta(hours=2), 
           'last 6 hours':   lambda now: now - timedelta(hours=6), 
           'Today':       lambda now: datetime.combine(now.date(), time()),
           'One day':     lambda now: now - timedelta(days=1),
           'Three days':  lambda now: datetime.combine(now - timedelta(days=3), time()), 
           'One week':    lambda now: datetime.combine(now - timedelta(days=7), time()), 
           'One month':   lambda now: datetime.combine(now - timedelta(days=30), time()), 
           'Three month': lambda now: datetime.combine(now - timedelta(days=90), time()),
           'One year':    lambda now: datetime.combine(now - timedelta(days=365), time()), 
           'All':         lambda now: datetime(2014, 11, 1, 0, 0) }

def getRelativeDatetime( span, custom, now=None, useTimezone=False ):
    if now is None:
        if useTimezone:
            now = datetime.utcnow().replace(tzinfo= pytz.utc )
        else:
            now = datetime.now()
    return lookup.get(span, lambda now: custom)(now)


if __name__ == "__main__":
    for name in timespans:
        print(name, getRelativeDatetime(name, datetime(2015, 11, 1, 0, 0) ))
        print(name, getRelativeDatetime(name, datetime(2015, 11, 1, 0, 0), useTimezone=True ))
