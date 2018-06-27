# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
"""

Wrapper for python shelve module to be able to use it with the with expression.
It also includes default directory for storing of config files.

"""
import hashlib
import multiprocessing

import logging
import dill as pickle
import os.path
import sys
from PyQt5 import QtCore

from sqlalchemy import Column, String, Binary, Boolean, Integer, DateTime, PickleType, func
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
import yaml
import datetime
import copy
from wrapt import synchronized
from threading import Thread, Event

from modules.hasher import hexdigest

Base = declarative_base()
defaultcategory = 'main'


class ShelveEntry(Base):
    __tablename__ = "shelve"
    category = Column(String, primary_key=True )
    key = Column(String, primary_key=True)
    pvalue = Column(Binary)
    
    def __init__(self,key,value,category=defaultcategory):
        self.category = category
        self.key = key
        self.pvalue = pickle.dumps(value, 2)
        
    def __repr__(self):
        return "<'{0}.{1}' '{2}'>".format(self.category, self.key, self.value)
       
    @property
    def value(self):
        return pickle.loads(self.pvalue)  # , encoding='Latin-1')
        
    @value.setter
    def value(self, value):
        self.pvalue = pickle.dumps(value, 2)


class DatabaseVersion(Base):
    __tablename__ = os.path.splitext(os.path.basename(sys.argv[0]))[0].lower() + "_version"
    id = Column(Integer, primary_key=True)
    upd_date = Column(DateTime(timezone=True), default=datetime.datetime.now)

    def __init__(self, id):
        self.id = id


class PgShelveEntry(Base):
    __tablename__ = os.path.splitext(os.path.basename(sys.argv[0]))[0].lower() + "_pg_shelve"
    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False)
    upd_date = Column(DateTime(timezone=True), default=datetime.datetime.now)
    pvalue = Column(Binary)
    digest = Column(Binary)
    active = Column(Boolean)

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.active = True

    @property
    def value(self):
        try:
            v = pickle.loads(self.pvalue)
        except Exception as e:
            logging.getLogger(__name__).exception(e)
            raise
        return v

    @value.setter
    def value(self, value):
        try:
            self.pvalue = pickle.dumps(value, 4)
            self.digest = hexdigest(self.pvalue, hashlib.sha224).encode()
        except Exception as e:
            logging.getLogger(__name__).error("Pickling of {0} failed {1}".format(self.key, str(e)))


class configshelve:
    version = 2
    def __init__(self, dbConnection, filename=None, loadFromDate=None, filetype='sqlite'):
        self.database_conn_str = dbConnection.connectionString
        self.engine = create_engine(self.database_conn_str, echo=dbConnection.echo)
        self.buffer = dict()
        self.dbContent = dict()
        self.dbDigest = dict()
        self.filename = filename
        self.loadFromDate = loadFromDate
        self.filetype = filetype
        self.commit_ready = None

    @synchronized
    def loadFromDatabase(self):
        try:
            v = self.session.query(DatabaseVersion).order_by(DatabaseVersion.id.desc()).first()
            databaseVersion = v.id if v is not None else 0
        except NoResultFound:
            databaseVersion = 0
        if self.version > databaseVersion:
            self.upgradeDatabase(databaseVersion)
        if self.loadFromDate:
            subquery = self.session.query(func.max(PgShelveEntry.id)).filter(PgShelveEntry.upd_date < self.loadFromDate).group_by(PgShelveEntry.key)
        else:
            subquery = self.session.query(func.max(PgShelveEntry.id)).group_by(PgShelveEntry.key)
        for record in self.session.query(PgShelveEntry).filter(PgShelveEntry.id.in_(subquery)).filter(PgShelveEntry.active).all():
            try:
                self.buffer[record.key] = copy.deepcopy(record.value)
                self.dbContent[record.key] = record.value
                self.dbDigest[record.key] = record.digest
            except Exception as e:
                logging.getLogger(__name__).exception(e)
                logging.getLogger(__name__).warning("configuration parameter '{0}' cannot be read from database. ({1})".format(record.key, e))

    def upgradeDatabase(self, databaseVersion):
        if databaseVersion < 1:
            self._commitToDatabase(forcePickle=True)
        if databaseVersion < 2:
            connection = self.engine.connect()
            trans = connection.begin()
            try:
                self.engine.execute("alter table {} add column active boolean".format(PgShelveEntry.__tablename__))
                self.engine.execute("update {} set active=True".format(PgShelveEntry.__tablename__))
                trans.commit();
            except Exception as e:
                print(e)
                trans.rollback()
                raise
        self.session.add(DatabaseVersion(self.version))
        self.session.commit()
        self.session = self.Session()

    @synchronized
    def loadFromFile(self, filename, filetype='sqlite'):
        if filetype == 'sqlite':
            engine = create_engine('sqlite:///' + filename, echo=False)
            Session = sessionmaker(bind=engine)
            session = Session()
            for record in session.query(ShelveEntry).all():
                try:
                    self.buffer[record.key] = record.value
                except Exception as e:
                    logging.getLogger(__name__).warning("configuration parameter '{0}' cannot be read from file {1} ({2})".format(record.key, filename, e))
            session.commit()
        elif filetype == 'yaml':
            with open(filename, 'r') as f:
                self.buffer.update(yaml.load(f))

    def commitToDatabase(self):
        self.commit_ready = Event()
        t = Thread(target=self._commitToDatabase)
        t.start()

    @synchronized
    def _commitToDatabase(self, forcePickle=False):
        for key, value in self.buffer.items():
            if self.dbContent.get(key) is None or self.dbContent.get(key) != value or forcePickle:
                entry = PgShelveEntry(key, value)
                if self.dbDigest.get(key) != entry.digest:
                    self.session.add(entry)
                    self.dbContent[key] = copy.deepcopy(value)
                    self.dbDigest[key] = entry.digest
        self.session.commit()
        self.session = self.Session()
        if self.commit_ready:
            self.commit_ready.set()
        
    @synchronized
    def saveConfig(self, copyTo=None, yamlfile=None):
        if copyTo:
            engine = create_engine('sqlite:///' + copyTo, echo=False)
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            session = Session()
            for key, value in self.buffer.items():
                session.add(ShelveEntry(key, value))
            session.commit()
        if yamlfile:
            with open(yamlfile, 'w') as f:
                print(yaml.dump(self.buffer, default_flow_style=False), file=f)
        self.commitToDatabase()

    @synchronized
    def sessionCommit(self):
        self.session.commit()

    def __enter__(self):
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.loadFromDatabase()
        if self.filename:
            self.loadFromFile(self.filename, self.filetype)
        return self
        
    def __exit__(self, exittype, value, tb):
        self.commitToDatabase()
        if self.commit_ready is not None:
            self.commit_ready.wait()
        self.sessionCommit()

    @synchronized
    def __setitem__(self, key, value):
        self.buffer[key] = value

    @synchronized
    def __delitem__(self, key):
        try:
            elem = self.session.query(PgShelveEntry).filter(PgShelveEntry.key==key).order_by(PgShelveEntry.upd_date.desc()).first()
            elem.active = False
            self.session.commit()
            self.session = self.Session()
        except NoResultFound:
            return False
        return True

    @synchronized
    def __getitem__(self, key):
        return self.buffer[key]

    @synchronized
    def items_startswith(self, key_start):
        start_length = len(key_start)
        return [(key[start_length:].strip("."), value) for key, value in self.buffer.items() if key.startswith(key_start)]

    @synchronized
    def set_string_dict(self, prefix, string_dict):
        for key, value in string_dict.items():
            self.buffer[prefix + "." + key] = value
            
    @synchronized
    def __contains__(self, key):
        return key in self.buffer

    @synchronized
    def get(self, key, default=None):
        return self.buffer.get(key, default)

    @synchronized
    def __next__(self):
        logging.getLogger(__name__).error("__next__ not implemented")
        
    @synchronized
    def open(self):
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.isOpen = True
        
    @synchronized
    def close(self):
        self.session.commit()
        self.isOpen = False


if __name__ == "__main__":
    with configshelve("new-test.db") as d:
        d['Peter'] = 'Maunz'
        print('Peter'in d)
        print(('Peter', 'main') in d)
        print(('main', 'Peter') in d)
        
