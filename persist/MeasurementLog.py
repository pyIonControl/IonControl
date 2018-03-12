# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Interval, Float, Boolean
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy import create_engine
from modules.quantity import Q, is_Q
from sqlalchemy.exc import ProgrammingError, InvalidRequestError, IntegrityError
import logging
from sqlalchemy import ForeignKey
from modules.Observable import Observable
import weakref
from modules.SequenceDict import SequenceDict 
from datetime import datetime, timedelta, time

Base = declarative_base()

class Study(Base):
    __tablename__ = "studies"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    startDate = Column(DateTime(timezone=True))
    endDate = Column(DateTime(timezone=True))

class Measurement(Base):
    __tablename__ = "measurements"
    id = Column(Integer, primary_key=True)
    scanType = Column(String, nullable=False)
    scanName = Column(String, nullable=False)
    scanParameter = Column(String)
    scanTarget = Column(String)
    scanPP = Column(String)
    evaluation = Column(String, nullable=False)
    startDate = Column(DateTime(timezone=True))
    duration = Column(Interval)
    filename = Column(String)
    comment = Column(String)
    longComment = Column(String)
    study_id = Column(Integer, ForeignKey('studies.id'))
    study = relationship( "Study", backref=backref('measurements', order_by=id))
    failedAnalysis = Column(String)
    
    def __init__(self, *args, **kwargs):
        super(Measurement, self).__init__(*args, **kwargs)
        self._plottedTraceList = list()
        self.isPlotted = None
        
    def addResult(self, result):
        self.results.append( result )
        
    @property
    def plottedTraceList(self):
        self._plottedTraceList = [item for item in self._plottedTraceList if item() is not None] if hasattr(self, '_plottedTraceList') else list()
        return [item() for item in self._plottedTraceList]
    
    @plottedTraceList.setter
    def plottedTraceList(self, plottedTraceList):
        self._plottedTraceList = [weakref.ref(item) for item in plottedTraceList]
        
    def parameterByName(self, space, name):
        if not hasattr(self, '_parameterIndex') or len(self._parameterIndex) != len(self.parameters):
            self._parameterIndex = dict( ((param.space.name, param.name), index) for index, param in enumerate(self.parameters)  )
        return self.parameters[ self._parameterIndex[(space, name)] ] if (space, name) in self._parameterIndex else None
            
    def resultByName(self, name):
        if not hasattr(self, '_resultIndex') or len(self._resultIndex) != len(self.results):
            self._resultIndex = dict( (result.name, index) for index, result in enumerate(self.results)  )
        return self.results[ self._resultIndex[name] ] if name in self._resultIndex else None
            
        

class Space(Base):
    __tablename__ = 'space'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)    

class Result(Base):
    __tablename__ = 'results'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    _value = Column(Float)
    _bottom = Column(Float)
    _top = Column(Float) 
    unit = Column(String)
    manual = Column(Boolean, default=False)
    measurement_id = Column(Integer, ForeignKey('measurements.id'))
    measurement = relationship( "Measurement", backref=backref('results', order_by=id))
    
    def __init__(self, *args, **kwargs):
        updates = [(param, kwargs.pop(param)) for param in ['value', 'bottom', 'top'] if param in kwargs] 
        super( Result, self ).__init__(*args, **kwargs)
        for name, value in updates:
            setattr( self, name, value)
    
    @property
    def value(self):
        return Q(self._value, self.unit) if self._value is not None else None
    
    @value.setter
    def value(self, magValue ):
        if self.unit is None:
            if is_Q(magValue):
                self._value, self.unit = magValue.m, "{:~}".format(magValue.units)
            else:
                self._value = magValue
        else:
            self._value = magValue.m_as(self.unit)
        
    @property
    def bottom(self):
        return Q(self._bottom, self.unit) if self._bottom is not None else None
    
    @bottom.setter
    def bottom(self, magValue ):
        if magValue is None:
            self._bottom = None     
        elif self.unit is None:
            if is_Q(magValue):
                self._bottom, self.unit = magValue.m, "{:~}".format(magValue.units)
            else:
                self._bottom = magValue
        else:
            self._bottom = magValue.m_as(self.unit)
        
    @property
    def top(self):
        return Q(self._top, self.unit) if self._top is not None else None
    
    @top.setter
    def top(self, magValue ):
        if magValue is None:
            self._bottom = None     
        elif self.unit is None:
            if is_Q(magValue):
                self._top, self.unit = magValue.m, "{:~}".format(magValue.units)
            else:
                self._top = magValue
        else:
            self._top = magValue.m_as(self.unit)
            
        
class Parameter(Base):
    __tablename__ = 'parameters'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    _value = Column(Float)
    unit = Column(String)
    definition = Column(String)
    manual = Column(Boolean, default=False)
    measurement_id = Column(Integer, ForeignKey('measurements.id'))
    measurement = relationship( "Measurement", backref=backref('parameters', order_by=id)) # , collection_class=attribute_mapped_collection('name')
    space_id = Column(Integer, ForeignKey('space.id'))
    space = relationship( "Space", backref=backref('parameters', order_by=id))
    
    def __init__(self, *args, **kwargs):
        if 'value' in kwargs:
            myvalue = kwargs['value']
            kwargs.pop('value')
            super( Parameter, self ).__init__(*args, **kwargs)
            self.value = myvalue
        else:
            super( Parameter, self ).__init__(*args, **kwargs)
            
    
    @property
    def value(self):
        return Q(self._value, self.unit)
    
    @value.setter
    def value(self, magValue ):
        if is_Q(magValue):
            self._value, self.unit = magValue.m, "{:~}".format(magValue.units)
        else:
            self._value = magValue
        
class MeasurementContainer(object):
    def __init__(self, dbConnection):
        self.database_conn_str = dbConnection.connectionString
        self.engine = create_engine(self.database_conn_str, echo=dbConnection.echo)
        self.studies = list()
        self.measurements = list()
        self.measurementDict = dict() #key - startDate, val - Measurement
        self.spaces = list()
        self.isOpen = False
        self.beginInsertMeasurement = Observable()
        self.endInsertMeasurement = Observable()
        self.studiesObservable = Observable()
        self.measurementsUpdated = Observable()
        self.scanNamesChanged = Observable()
        self._scanNames = SequenceDict()
        self._scanNameFilter = None
        self.fromTime = datetime(2014, 11, 1, 0, 0)
        self.toTime = datetime.combine((datetime.now()+timedelta(days=1)).date(), time())
        
    def setScanNameFilter(self, scanNameFilter):
        if self._scanNameFilter!=scanNameFilter:
            self._scanNameFilter = scanNameFilter
            self.query(self.fromTime, self.toTime, self._scanNameFilter)
        
    def open(self):
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.session = self.Session()
        self.isOpen = True
        
    def close(self):
        self.session.commit()
        self.isOpen = False

    def __enter__(self):
        if not self.isOpen:
            self.open()
        return self
        
    def __exit__(self, exittype, value, tb):
        self.session.commit()

    def addMeasurement(self, measurement):
        try:
            self.session.add( measurement )
            self.session.commit()
            self.measurementDict[str(measurement.startDate)] = measurement
            if self._scanNameFilter is None or measurement.scanName in self._scanNameFilter:
                self.beginInsertMeasurement.fire(first=0, last=0)
                self.measurements.insert( 0, measurement )
                self.endInsertMeasurement.firebare()
            if measurement.scanName not in self._scanNames:
                self._scanNames.setdefault( measurement.scanName, True )
                self.scanNamesChanged.fire( scanNames=self._scanNames )
        except (InvalidRequestError, IntegrityError, ProgrammingError) as e:
            logging.getLogger(__name__).warning( str(e) )
            self.session.rollback()
            self.session = self.Session()
        
    def commit(self):
        try:
            self.session.commit()
        except (InvalidRequestError, IntegrityError, ProgrammingError) as e:
            logging.getLogger(__name__).warning( str(e) )
            self.session.rollback()
            self.session = self.Session()
        
    def query(self, fromTime, toTime, scanNameFilter=None):
        logging.getLogger(__name__).info("Starting query from {} to {} scannames {}".format(fromTime, toTime, scanNameFilter))
        if scanNameFilter is None:
            self.measurements = self.session.query(Measurement).filter(Measurement.startDate>=fromTime).filter(Measurement.startDate<=toTime).order_by(Measurement.id.desc()).all() 
            self._scanNames = SequenceDict(((m.scanName, self._scanNames.get(m.scanName, True)) for m in self.measurements))
            self._scanNames.sort()
        else:
            self.measurements = self.session.query(Measurement).filter(Measurement.startDate>=fromTime).filter(Measurement.startDate<=toTime).filter(Measurement.scanName.in_(scanNameFilter)).order_by(Measurement.id.desc()).all() 
            scanNames = self.session.query(Measurement.scanName).filter(Measurement.startDate>=fromTime).filter(Measurement.startDate<=toTime).group_by(Measurement.scanName).order_by(Measurement.scanName).all()
            self._scanNames = SequenceDict(((name, name in scanNameFilter) for name, in scanNames))
        self.scanNamesChanged.fire( scanNames=self.scanNames )
        self.measurementsUpdated.fire(measurements=self.measurements)
        self.fromTime, self.toTime = fromTime, toTime
        logging.getLogger(__name__).info("Query complete.")
    
    def refreshLookups(self):
        """Load the basic short tables into memory
        those are: Space"""
        try:
            self.spaces = dict(( (s.name, s) for s in self.session.query(Space).all() ))
        except (InvalidRequestError, IntegrityError, ProgrammingError) as e:
            logging.getLogger(__name__).warning( str(e) )
            self.session.rollback()
            self.session = self.Session()
        
    def getSpace(self, name):
        if name not in self.spaces:
            self.refreshLookups()
        if name in self.spaces:
            return self.spaces[name]
        s = Space(name=name)
        self.spaces[name] = s
        return s
    
    @property
    def scanNames(self):
        return self._scanNames
        
        
if __name__=='__main__':
    with MeasurementContainer("postgresql://python:yb171@localhost/ioncontrol") as d:
        d.addMeasurement( Measurement(scanName='test'))

        
    