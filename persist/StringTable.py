# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
import hashlib

from sqlalchemy import Column, String, Float, DateTime, Integer, Index
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.exc import InvalidRequestError, IntegrityError
from sqlalchemy.exc import OperationalError

Base = declarative_base()


class DataEntry(Base):
    __tablename__ = "data_table"
    id = Column(Integer, primary_key=True)
    identifier = Column(String, nullable=False, unique=True)
    data = Column(String, nullable=False)

    def __init__(self, data, identifier=None):
        self.data = data
        self.identifier = DataEntry.calcIdentifier(data) if identifier is None else identifier

    @classmethod
    def calcIdentifier(cls, data):
        return hashlib.sha1(data.encode('utf-8')).hexdigest()


class DataStore(set):
    def __init__(self, dbConnection):
        self.database_conn_str = dbConnection.connectionString
        self.engine = create_engine(self.database_conn_str, echo=dbConnection.echo)
        self.databaseAvailable = False
        super(DataStore, self).__init__()

    def refresh(self):
        self.update(set(s.identifier for s in self.session.query(DataEntry.identifier).all()))

    def commit(self):
        self.session.commit()

    def open_session(self):
        self.__enter__()

    def close_session(self):
        if self.databaseAvailable:
            self.session.commit()

    def __enter__(self):
        try:
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
            self.session = self.Session()
            self.refresh()
            self.databaseAvailable = True
        except OperationalError as e:
            logging.getLogger(__name__).info(str(e))
            self.databaseAvailable = False
        return self

    def __exit__(self, exittype, value, tb):
        self.session.commit()

    def addData(self, data):
        if self.databaseAvailable:
            try:
                identifier = DataEntry.calcIdentifier(data)
                if identifier not in self:
                    elem = DataEntry(data, identifier=identifier)
                    self.session.add(elem)
                    self.commit()
                    self.add(identifier)
                return identifier
            except (InvalidRequestError, IntegrityError) as e:
                self.session.rollback()
                self.session = self.Session()
                self.refresh()
                logging.getLogger(__name__).error(str(e))

    def __getitem__(self, identifier):
        if identifier not in self:
            raise KeyError
        return self.session.query(DataEntry.data).filter(DataEntry.identifier == identifier).one().data


if __name__ == "__main__":
    from persist.DatabaseConnectionSettings import DatabaseConnectionSettings
    with DataStore(DatabaseConnectionSettings(user='python', database='ioncontrol', password='yb171', host='localhost', echo=True)) as d:
        id1 = d.addData('First test')
        id2 = d.addData('Second test')
        print(d[id1])
        print(d[id2])

