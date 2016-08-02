# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging

from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, Index
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.exc import InvalidRequestError, IntegrityError
from sqlalchemy.exc import OperationalError

from modules.quantity import is_Q
from persist.DatabaseConnectionSettings import DatabaseConnectionSettings

Base = declarative_base()
    
    
class HistoryException(Exception):
    pass
    
class HistorySource(Base):
    __tablename__ = "history_source"
    id = Column(Integer, primary_key = True)
    space = Column(String, nullable=False, )
    name = Column(String, nullable=False, unique=True )
    __table_args__ = (Index('history_source_index', "space", "name", unique=True), )    
    
class ValueHistoryEntry(Base):
    __tablename__ = "history_value"
    source_id = Column(Integer, ForeignKey('history_source.id'), primary_key=True )
    source = relationship( HistorySource, backref=backref('history', uselist=True, cascade='delete,all'))
    value = Column(Float, nullable=False)
    bottom = Column(Float)
    top = Column(Float)
    unit = Column(String)
    upd_date = Column(DateTime(timezone=True), primary_key=True)
    
    def __init__(self, sourceObj, value, unit, upd_date):
        self.source = sourceObj
        self.value = value
        self.unit = unit
        self.upd_date = upd_date
        
    def __repr__(self):
        return "<'{0}.{1}' {2} {3} @ {4}>".format(self.source.space, self.source.name, self.value, self.unit, self.upd_date)
        
    
class ValueHistoryStore:
    def __init__(self, dbConnection):
        self.database_conn_str = dbConnection.connectionString
        self.engine = create_engine(self.database_conn_str, echo=dbConnection.echo)
        self.sourceDict = dict()
        self.databaseAvailable = False

    def rename(self, space, oldsourcename, newsourcename):
        if (space, oldsourcename) not in self.sourceDict:
            raise HistoryException("cannot rename {0} to {1} because {0} does not exist in database".format(oldsourcename, newsourcename))
        if (space, newsourcename) in self.sourceDict:
            raise HistoryException("cannot rename {0} to {1} because {1} already exists in database".format(oldsourcename, newsourcename))
        elem = self.session.query(HistorySource).filter(HistorySource.space==space).filter(HistorySource.name==oldsourcename).first()
        elem.name = newsourcename
        self.commit()
        self.sourceDict[(space, newsourcename)] = self.sourceDict.pop((space, oldsourcename))
        
    def getSource(self, space, source):
        if space is None or source is None:
            raise HistoryException('Space or source cannot be None')
        if (space, source) in self.sourceDict:
            s = self.sourceDict[(space, source)]
            self.session.add(s)
            return s
        else:
            s = HistorySource( space=space, name=source )
            self.session.add(s)
            self.sourceDict[(space, source)] = s
            return s
        
    def refreshSourceDict(self):
        self.sourceDict = dict( [((s.space, s.name), s) for s in self.session.query(HistorySource).all()] )
        return self.sourceDict    
        
    def getHistory(self, space, source, fromTime, toTime ):
        if toTime is not None:
            return self.session.query(ValueHistoryEntry).filter(ValueHistoryEntry.source==self.getSource(space, source)).\
                                                  filter(ValueHistoryEntry.upd_date>fromTime).\
                                                  filter(ValueHistoryEntry.upd_date<toTime).order_by(ValueHistoryEntry.upd_date).all()
        else:
            return self.session.query(ValueHistoryEntry).filter(ValueHistoryEntry.source==self.getSource(space, source)).\
                                                  filter(ValueHistoryEntry.upd_date>fromTime).order_by(ValueHistoryEntry.upd_date).all()
        
    def commit(self, copyTo=None ):
        self.session.commit()
#        self.session = self.Session()

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
            self.refreshSourceDict()
            self.databaseAvailable = True
        except OperationalError as e:
            logging.getLogger(__name__).info( str(e))
            self.databaseAvailable = False
        return self
        
    def __exit__(self, exittype, value, tb):
        self.session.commit()
        
    def add(self, space, source, value, unit, upd_date, bottom=None, top=None):
        if self.databaseAvailable:
            try:
                if is_Q(value):
                    value, unit = value.m, "{:~}".format(value.units)
                    if is_Q(bottom):
                        bottom = bottom.m_as(unit)
                    if is_Q(top):
                        top = top.m_as(unit)
                if space is not None and source is not None:
                    paramObj = self.getSource(space, source)
                    if is_Q(value):
                        value, unit = value.m, "{:~}".format(value.units)
                    elem = ValueHistoryEntry(paramObj, value, unit, upd_date)
                    self.session.add(elem)
                    elem.value = value
                    if bottom is not None:
                        elem.bottom = bottom
                    if top is not None:
                        elem.top = top
                    self.commit()
            except (InvalidRequestError, IntegrityError) as e:
                self.session.rollback()
                self.session = self.Session()
                self.refreshSourceDict()
                logging.getLogger(__name__).error(str(e))
                
        
    def get(self, space, source ):
        return self.session.query(ValueHistoryEntry).filter(ValueHistoryEntry.source==self.getSource(space, source) )
                    
    def open(self):
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.session = self.Session()
        self.isOpen = True
        
    def close(self):
        self.session.commit()
        self.isOpen = False
        
if __name__ == "__main__":
    import datetime
    with ValueHistoryStore(DatabaseConnectionSettings(user='python', database='ioncontrol', password='yb171', host='localhost')) as d:
        d.add('test', 'Peter', 12, 'mm', datetime.datetime.now())
        d.add('test', 'Peter', 13, 'mm', datetime.datetime.now())
        d.add('test', 'Peter', 14, 'mm', datetime.datetime.now(), bottom=3, top=15 )
        

