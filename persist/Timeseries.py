from ProjectConfig.Project import getProject
from externalParameter.persistence import persistenceProviders, persistenceDict

try:
    from influxdb import InfluxDBClient

    class TimeseriesPersist:
        store = None
        name = "Timeseries persist"

        def __init__(self):
            self.initialized = False
            self.active = True

        def __setstate__(self, state):
            self.__dict__.update(state)
            self.initialized = False

        def initDB(self):
            if TimeseriesPersist.store is None:
                prj = getProject()
                self.projectName = prj.name
                self.active = False
                if 'Timeseries Database' in prj.software:
                    dbs = prj.software['Timeseries Database']
                    if dbs:
                        db = list(dbs.values())[0]
                        TimeseriesPersist.store = InfluxDBClient(host=db.get('host'), port=8086,
                                                                 database=db.get('database'))
                        self.active = True
            self.initialized = True

        def persist(self, space, source, time, value, minval=None, maxval=None, unit=None):
            if not self.active:
                return
            if not self.initialized:
                self.initDB()
            if source:
                 TimeseriesPersist.store.write_points([{
                    "measurement": source,
                    "tags": {
                        "space": space,
                        "project": self.projectName,
                    },
                    "fields": {
                        "value": value,
                        "minval": minval,
                        "maxval": maxval,
                        "unit": unit
                    },
                     "time": time if time > 1000000000000000000 else int(time * 1000000000)
                }])

        def rename(self, space, oldsourcename, newsourcename):
            pass

        def paramDef(self):
            return []

        def sourceDict(self):
            return {}

    persistenceProviders.append(TimeseriesPersist)
    persistenceDict[TimeseriesPersist.name] = TimeseriesPersist

except:
    pass