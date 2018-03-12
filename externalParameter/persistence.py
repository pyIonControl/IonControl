# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from persist.ValueHistory import ValueHistoryStore
from datetime import datetime
from ProjectConfig.Project import getProject
from modules.Observable import Observable


class DBPersist:
    name = "DB Persist"
    newPersistData = Observable()
    engines = None

    def __init__(self):
        self.initialized = False

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.initialized = False

    def initDB(self):
        if DBPersist.engines is None:
            DBPersist.engines = [engine() for engine in persistenceProviders]
        self.initialized = True

    def persist(self, space, source, time, value, minval=None, maxval=None, unit=None):
        if not self.initialized:
            self.initDB()
        if source:
            for e in DBPersist.engines:
                e.persist(space, source, time, value, minval, maxval, unit)
            ts = datetime.fromtimestamp(time)
            self.newPersistData.fire(space=space, parameter=source, value=value, unit=unit, timestamp=ts, bottom=minval,
                                     top=maxval)

    def rename(self, space, oldsourcename, newsourcename):
        if not self.initialized:
            self.initDB()
        for e in DBPersist.engines:
            e.rename(space, oldsourcename, newsourcename)

    def paramDef(self):
        return []

    def sourceDict(self):
        d = dict()
        for e in DBPersist.engines:
            d.update(e.sourceDict())
        return d


class SQLDBPersist:
    store = None
    name = "SQL DB Persist"
    newPersistData = Observable()
    def __init__(self):
        self.initialized = False

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.initialized = False
        
    def initDB(self):
        dbConnection = getProject().dbConnection
        if SQLDBPersist.store is None:
            SQLDBPersist.store = ValueHistoryStore(dbConnection)
            SQLDBPersist.store.open_session()
        self.initialized = True
        
    def persist(self, space, source, time, value, minval=None, maxval=None, unit=None):
        if not self.initialized:
            self.initDB()
        if source:
            ts = datetime.fromtimestamp(time)
            SQLDBPersist.store.add( space, source, value, unit, ts, bottom=minval, top=maxval )
            self.newPersistData.fire( space=space, parameter=source, value=value, unit=unit, timestamp=ts, bottom=minval, top=maxval )

    def rename(self, space, oldsourcename, newsourcename):
        if not self.initialized:
            self.initDB()
            SQLDBPersist.store.rename(space, oldsourcename, newsourcename)

    def paramDef(self):
        return []

    def sourceDict(self):
        if not self.initialized:
            self.initDB()
        return SQLDBPersist.store.sourceDict

persistenceDict = { DBPersist.name: DBPersist }
persistenceProviders = [SQLDBPersist]