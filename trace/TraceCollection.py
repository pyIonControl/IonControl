# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import json
from collections import defaultdict
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_BZIP2

import yaml
from dateutil import parser
import io
from itertools import zip_longest
import math
import os.path
import h5py
import copy
import pickle

import numpy

from modules.XmlUtilit import prettify
from modules.enum import enum
import lxml.etree as ElementTree
import time
import pytz
from modules.DataDirectory import DataDirectory
import logging
from collections import OrderedDict

from trace.PlottedStructure import PlottedStructure
from trace.PlottedTrace import PlottedTrace, PlottedTraceProperties
from trace.StructuredUnpickler import StructuredUnpickler

try:
    from fit import FitFunctions
    FitFunctionsAvailable = True
except:
    FitFunctionsAvailable = False

filetypes = {'.hdf': 'hdf5', '.hdf5': 'hdf5', '.txt': 'text', '.zip': 'zip'}
extensions = {'text': '.txt', 'hdf5': '.hdf5', 'zip': '.zip'}

def file_type(filename, default):
    return filetypes.get(os.path.splitext(filename)[1], default)


def replaceExtension(filename, extension):
    extension = extension if extension[0] == '.' else '.{0}'.format(extension)
    return os.path.splitext(filename)[0] + extension


class TraceException(Exception):
    pass

class ColumnSpec(list):
    def toXmlElement(self, root):
        myElement = ElementTree.SubElement(root, 'ColumnSpec', {})
        myElement.text = ", ".join( self )
        return myElement
    
    @staticmethod
    def fromXmlElement(element):
        return ColumnSpec( element.text.split(", ") )
    

def to_float(s):
    try:
        return float(s)
    except ValueError:
        return float("nan")


class PlottingList(list):
    def toXmlElement(self, root):
        myElement = ElementTree.SubElement(root, 'TracePlottingList', {})
        for traceplotting in self:
            traceplotting.toXML(myElement)
        return myElement

    def toHdf5(self, group):
        mygroup = group.require_group('TracePlottingList')
        for traceplotting in self:
            g = mygroup.require_group(traceplotting.name)
            for name in PlottedTrace.serializeFields:
                attr = getattr(traceplotting, name)
                g.attrs[name] = attr if attr is not None else ''
            if traceplotting.fitFunction:
                traceplotting.fitFunction.toHdf5(g)

    @staticmethod
    def fromXmlElement(element, traceCollection):
        logger = logging.getLogger(__name__)
        l = PlottingList()
        for plottingelement in element.findall("TracePlotting"):
            plotting = PlottedTrace(traceCollection)
            # added workaraound for PlottedTraceProperties since xml loading via findall isn't recursive and returned
            # a string instance of the PlottedTraceProperties object, probably best to derive a new class from ElementTree
            attribdict = dict(plottingelement.attrib)
            if "properties" in attribdict.keys() and isinstance(attribdict['properties'], str):
                try:
                    attribdict['properties'] = PlottedTraceProperties(**plottingelement.findall("PlottedTraceProperties")[0].attrib)
                except Exception:
                    logger.warning("Couldn't resolve PlottedTraceProperties in {}".format(traceCollection.filename))
            plotting.__setstate__(attribdict)
            plotting.type = int(plotting.type) if hasattr(plotting, 'type') else 0
            if plottingelement.find("FitFunction") is not None:
                plotting.fitFunction = FitFunctions.fromXmlElement(plottingelement.find("FitFunction"))
            else:
                plotting.fitFunction = None
            l.append(plotting)
        # for plottingelement in element.findall("StructurePlotting"):
        #     plotting = PlottedStructure()
        #     plotting.__setstate__(plottingelement.attrib)
        #     l.append(plotting)
        return l

    @staticmethod
    def fromHdf5(group):
        l = PlottingList()
        for name, g in group.items():
            plotting = PlottedTrace()
            plotting.__setstate__(g.attrs)
            if "FitFunction" in g:
                plotting.fitFunction = FitFunctions.fromHdf5(g.get("FitFunction"))
            l.append(plotting)
        return l
    
    def __str__(self):
        return "TracePlotting length {0}".format(len(self))        

varFactory = { 'str': str,
               'datetime': lambda s: parser.parse(s), #datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f'),
               'float': float,
               'int': int }


class keydefaultdict(OrderedDict):
    def __init__(self, default_factory, *args):
        super().__init__(*args)
        self.default_factory = default_factory

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        else:
            ret = self[key] = self.default_factory(self, key)
            return ret


class FormatDict(dict):
    def __missing__(self, key):
        ret = self[key] = 'pkl'
        return ret


class TraceCollection(keydefaultdict):
    """ Class to encapsulate a collection of traces with a common array of x values (or a single trace).

    This class contains the data for all the traces, and takes care of saving and loading the traces from file
    It inherits from defaultdict and the dictionary holds the columns

    Attributes:
        x (list[float]): array of x values
        y (list[float]): array of y values for single trace
        name (str): name associated with trace collection
        description (dict): description data
        description["comment"] (str): comment to add to file
        description["traceCreation"] (str): the time the collection was created
        filenamePattern (str): filename pattern to use when saving the trace
        autosave (bool): if True, trace collection will be saved as soon as filenamePattern is set
        saved (bool): True if trace collection has been saved
        filename (str): full path to file
        fileleaf (str): name only
        filepath (str): path only
        columnNames (list[str]): all column names in the saved file
    """
    def __init__(self, record_timestamps=False):
        super(TraceCollection, self).__init__(self.defaultColumn)
        """Construct a trace object."""
        self.name = "noname" #name to display in table of traces
        self.description = dict()
        self.description["comment"] = ""
        self.description["name"] = ""
        self.description["traceCreation"] = datetime.now(pytz.utc)
        self.autoSave = False
        self.saved = False
        self._filenamePattern = None
        self._fileType = 'text'
        self.filename = None
        self.filepath = None
        self.fileleaf = None
        self.rawdata = None
        self.description["tracePlottingList"] = PlottingList()
        self.record_timestamps = record_timestamps
        self.structuredData = keydefaultdict(self.get_structured_data)  #  Can contained structured data that can be json dumped
        self.structuredDataFormat = FormatDict()

    @staticmethod
    def get_structured_data(d, key):
        return dict()

    def __bool__(self):
        return True  # to remain backwards compatible with previous behavior

    @staticmethod
    def defaultColumn(d, key):
        if key == 'indexColumn' and 'x' in d:
            return list(range(len(d['x'])))
        return list()

    def varFromXmlElement(self, element, description):
        name = element.attrib['name']
        mytype = element.attrib['type']
        if mytype=='dict':
            mydict = dict()
            for subelement in element:
                self.varFromXmlElement(subelement, mydict)
            description[name] = mydict
        else:
            value = varFactory.get( mytype, str)( element.text )
            description[name] = value
            if name=='comment' and mytype=='str' and not element.text:
                description[name] = '' #avoid comments being set to the string 'None'
            if name=='name' and mytype=='str' and not element.text:
                description[name] = '' #avoid comments being set to the string 'None'

    def recordTimeinterval(self):
        self['timeTickFirst']
        self['timeTickLast']
    
    def timeintervalAppend(self, timeinterval, maxPoints=0):
        if 0 < maxPoints < len(self["timeTickFirst"]):
            self['timeTickFirst'] = self['timeTickFirst'][-maxPoints+1:0].append(timeinterval[0])
            self['timeTickLast'] = self['timeTickLast'][-maxPoints+1:0].append(timeinterval[1])
        else:
            self['timeTickFirst'].append(timeinterval[0])
            self['timeTickLast'].append(timeinterval[1])
        self.description["lastDataAquired"] = datetime.now(pytz.utc)
    
    @property
    def timeinterval(self):
        return (self['timeTickFirst'], self[ 'timeTickLast'] )
    
    @timeinterval.setter
    def timeinterval(self, val):
        self['timeTickFirst'], self['timeTickLast'] = val

    @property
    def x(self):
        return self['x']

    @x.setter
    def x(self, val):
        self['x'] = val

    @property
    def y(self):
        return self['y']
        
    @y.setter
    def y(self,val):
        self['y'] = val

    @property
    def comment(self):
        return self.description['comment']
    
    @comment.setter
    def comment(self, comment):
        self.description['comment'] = comment

    @property
    def tracename(self):
        return self.description['name']

    @tracename.setter
    def tracename(self, name):
        self.description['name'] = name

    @property
    def xUnit(self):
        return self.description.get('xUnit')
    
    @xUnit.setter
    def xUnit(self, magnitude):
        self.description['xUnit'] = magnitude
        
    @property
    def yUnit(self):
        return self.description.get('yUnit')
    
    @yUnit.setter
    def yUnit(self, magnitude):
        self.description['yUnit'] = magnitude

    @property
    def traceCreation(self):
        return self.description['traceCreation']

    @traceCreation.setter
    def traceCreation(self, date):
        self.description['traceCreation'] = date

    @property
    def filenamePattern(self):
        """Get the pattern of the file name"""
        return self._filenamePattern if self._filenamePattern else 'Untitled'

    @filenamePattern.setter
    def filenamePattern(self, pattern):
        """Set the filenamePattern. Use 'Untitled' as default. Save if autoSave is on."""
        self._filenamePattern = pattern if pattern else 'Untitled'
        self._fileType = file_type(pattern, self._fileType)
        if self.autoSave: self.save()

    def save(self, fileType=None, saveCopy=False):
        """save the trace to file"""
        if saveCopy or not self.saved:
            if fileType and fileType != self._fileType:
                self.filenamePattern = replaceExtension(self.filenamePattern, extensions[fileType])
                self._fileType = fileType
            self.filename, (self.filepath, name, ext) = DataDirectory().sequencefile(self.filenamePattern)
            self.fileleaf = name+ext
        elif fileType and fileType != self._fileType:
            self.filename = replaceExtension(self.filename, extensions[fileType])
            self._fileType = fileType
        if self._fileType == "text":
            self.saveText(self.filename)
        elif self._fileType == 'hdf5':
            try:
                self.saveHdf5(self.filename)
            except Exception as e:
                self.saveZip(replaceExtension(self.filename, extensions['zip']))
                logging.getLogger(__name__).warning("Failed to save hdf5 error '{}' saved zip instead".format(e))
        if self._fileType == 'zip' or self.structuredData:
            self.saveZip(replaceExtension(self.filename, extensions['zip']))
        return self.filename

    def saveText(self, filename):
        if filename:
            with open(filename,'w') as of:
                self.saveTraceHeaderXml(of)
                of.write(self.dataText())
            self.saved = True

    def dataText(self):
        return "\n".join("\t".join(map(repr, l)) for l in zip_longest(*list(self.values()), fillvalue=float('NaN')))

    def saveZip(self, filename):
        """Save data in zip file
        Data structure is
        header: xml header
        data: standard data file
        struct: folder with all structured data"""
        with ZipFile(filename, 'w', compression=ZIP_DEFLATED) as myzip:
            myzip.writestr('header.xml', prettify(self.headerXml()))
            myzip.writestr('data.txt', self.dataText())
            myzip.writestr('header.pkl', pickle.dumps({'header': self.header()}, -1))
            for name, value in self.structuredData.items():
                format = self.structuredDataFormat[name]
                name = 'structuredData/' + name
                if format.lower() in ['pkl', 'pickle']:
                    myzip.writestr(name + '.pkl', pickle.dumps(value))
                elif format.lower() == 'json':
                    myzip.writestr(name + '.json', json.dumps(value).encode())
                elif format.lower() == 'yaml':
                    myzip.writestr(name + '.yaml', yaml.dump(value).encode())
            myzip.writestr('structuredDataFormat.json', json.dumps(self.structuredDataFormat).encode())
        self.saved = True

    def loadZip(self, filename):
        with ZipFile(filename) as myzip:
            with myzip.open('header.pkl') as f:
                data = pickle.loads(f.read())
                self.description = data.get('header')
            with myzip.open('data.txt') as stream:
                data = []
                for line in stream:
                    line = line.strip()
                    data.append(list(map(to_float, line.split())))
            columnspec = self.description["columnspec"]
            for colname, d in zip(columnspec, zip(*data)):
                self[colname] = list(d)
            if 'fitfunction' in self.description and FitFunctionsAvailable:
                self.fitfunction = FitFunctions.fitFunctionFactory(self.description["fitfunction"])
            if "tracePlottingList" not in self.description:
                self.description["tracePlottingList"] = PlottingList(
                    [PlottedTrace(Trace=self, xColumn='x', yColumn='y', topColumn=None, bottomColumn=None,
                                 heightColumn=None,
                                 rawColumn=None, filtColumn=None, name="")])
            try:
                with myzip.open('structuredDataFormat.json') as f:
                    self.structuredDataFormat = FormatDict(json.loads(f.read().decode()))
                for filename in myzip.namelist():
                    if filename.startswith('structuredData/'):
                        leaf = filename[15:]
                        name = leaf.split('.', 1)[0]
                        format = self.structuredDataFormat[name]
                        with myzip.open(filename) as f:
                            if format.lower() in ['pkl', 'pickle']:
                                u = StructuredUnpickler(f)
                                self.structuredData[name] = u.load()
                            elif format.lower() == 'json':
                                self.structuredData[name] = json.loads(f.read().decode())
                            elif format.lower() == 'yaml':
                                self.structuredData[name] = yaml.load(f.read().decode())
            except Exception as e:
                logging.getLogger(__name__)
                logging.error("Failed to load zip file: {}".format(e))

    def saveHdf5(self, filename):
        # if self.rawdata:
        #     self.description["rawdata"] = self.rawdata.save()
        if hasattr(self,'fitfunction'):
            self.description["fitfunction"] = self.fitfunction
        if filename:
            with h5py.File(filename) as of:
                self.saveMetadata(of)
                colgroup = of.require_group('columns')
                for name, data in self.items():
                    colgroup.pop(name, None)
                    colgroup.create_dataset(name, data=data)
        self.saved = True

    def plot(self,penindex):
        """ plot the data, penindex >= 0 gives requests the style with this number,
        penindex = -1 uses the first available style, penindex = -2 uses the previous style
        """
        if hasattr( self, 'plotfunction' ):
            (self.plotfunction)(self,penindex)
    
    def varstr(self,name):
        """return the variable value as a string"""
        return str(self.description.get(name,""))
        
    def saveTraceHeader(self,outfile):
        """ save the header of the trace to outfile
        """
        self.description["fileCreation"] = datetime.now(pytz.utc)
        self.description.sort()
        for var, value in self.description.items():
            print("# {0}\t{1}".format(var, value), file=outfile)

    def header(self):
        if hasattr(self, 'fitfunction'):
            self.description["fitfunction"] = self.fitfunction
        columnspec = ColumnSpec(key for key in self.keys() if key is not None)
        self.description["columnspec"] = columnspec  # ",".join(columnspec)
        return self.description

    def headerXml(self):
        if hasattr(self, 'fitfunction'):
            self.description["fitfunction"] = self.fitfunction
        columnspec = ColumnSpec(key for key in self.keys() if key is not None)
        self.description["columnspec"] = columnspec  # ",".join(columnspec)
        root = ElementTree.Element('DataFileHeader')
        varsElement = ElementTree.SubElement(root, 'Variables', {})
        for name, value in sorted(self.description.items()):
            self.saveDescriptionElement(name, value, varsElement)
        return root

    def saveTraceHeaderXml(self,outfile):
        outfile.write(prettify(self.headerXml(),'# '))

    def saveMetadata(self, f):
        variables = f.require_group('variables')
        for name, value in self.description.items():
            self.saveMetadataElement(name, value, variables)

    def saveMetadataElement(self, name, value, variables):
        if hasattr(value,'toHdf5'):
            value.toHdf5(variables)
        if isinstance(value, dict):
            dictgroup = variables.require_group(name)
            for name_, value_ in value.items():
                self.saveMetadataElement(name_, value_, dictgroup)
        elif isinstance(value, (int, float)):
            variables.attrs[name] = value
        else:
            variables.attrs[name] = str(value)

    def saveDescriptionElement(self, name, value, element, use_json=False):
        if hasattr(value,'toXmlElement'):
            value.toXmlElement(element)
        elif use_json:
            e = ElementTree.SubElement(element, 'Element', {'name': name, 'type': 'json'})
            e.text = json.dumps(value)
        elif isinstance(value, dict):
            subElement = ElementTree.SubElement(element, 'Element', {'name': name, 'type': 'dict'})
            for subname, subvalue in value.items():
                self.saveDescriptionElement(subname, subvalue, subElement)           
        else:
            e = ElementTree.SubElement(element, 'Element', {'name': name, 'type': type(value).__name__})
            e.text = str(value)

    def loadTrace(self, filename):
        logger = logging.getLogger(__name__)
        self._fileType = file_type(filename, self._fileType)
        if self._fileType == "hdf5":
            try:
                self.loadTraceHdf5(filename)
            except Exception as e:
                logger.error("Could not load file {} error {}".format(filename, e))
        elif self._fileType == "zip":
            self.loadZip(filename)
        else:
            try:
                self.loadTracePlain(filename)
            except Exception as e:
                logger.error("Could not load file {} error {}".format(filename, e))

    def loadTraceHdf5(self, filename):
        self.filename = filename
        with h5py.File(self.filename) as f:
            for colname, dataset in f['columns'].items():
                self[colname] = list(dataset)
            tpelement = f.get("/variables/TracePlottingList")
            self.description["tracePlottingList"] = PlottingList.fromHdf5(tpelement) if tpelement is not None else None
            # for element in root.findall("/variables/Element"):
            #     self.varFromXmlElement(element, self.description)

    def loadTracePlain(self, filename):
        with io.open(filename,'r') as instream:
            position = instream.tell()
            firstline = instream.readline()
            instream.seek(position)
            if firstline.find("<?xml version") > 0 or firstline.find("<DataFileHeader>") > 0:
                self.loadTraceXml(instream)
            else:
                self.loadTraceText(instream)
                self.description["tracePlottingList"].append(PlottedTrace())
        self.filename = filename

    def loadTraceXml(self, stream):
        xmlstringlist = []
        data = []
        for line in stream:
            if line[0]=="#":
                xmlstringlist.append(line.lstrip("# "))
            else:
                data.append(list(map(to_float, line.split())))
        root = ElementTree.fromstringlist(xmlstringlist)
        columnspec = ColumnSpec.fromXmlElement(root.find("./Variables/ColumnSpec"))
        for colname, d in zip(columnspec, zip(*data)):
            if math.isnan(d[-1]):
                a = list(d[0:-1])
            else:
                a = list(d)
            self[colname] = a
        tpelement = root.find("./Variables/TracePlottingList")
        self.description["tracePlottingList"] = PlottingList.fromXmlElement(tpelement, self) if tpelement is not None else None
        for element in root.findall("./Variables/Element"):
            self.varFromXmlElement(element, self.description)
        for element in root.findall("./StructuredData/Element"):
            self.structuredData[element.name] = json.loads(element.text)

    def loadTraceText(self, stream):
        data = []
        self.description["columnspec"] = "x,y"
        for line in stream:
            line = line.strip()
            if not line or line[0]=='#':
                line = line.lstrip('# \t\r\n')
                if line.find('\t')<0:
                    a = line.split(None,1)
                else:
                    a = line.split('\t',1)
                if len(a)>1:
                    self.description[a[0]] = a[1]  
            else:
                data.append(list(map(to_float, line.split())))
        columnspec =  self.description["columnspec"].split(',')
        for colname, d in zip( columnspec, zip(*data) ):
            self[colname] = list(d)
        if 'fitfunction' in self.description and FitFunctionsAvailable:
            self.fitfunction = FitFunctions.fitFunctionFactory(self.description["fitfunction"])
        self.description["tracePlottingList"] = PlottingList(
            [PlottedTrace(xColumn='x', yColumn='y', topColumn=None, bottomColumn=None, heightColumn=None,
                          rawColumn=None, filtColumn=None, name="")])
            
    def setPlotfunction(self, callback):
        self.plotfunction = callback
        
    def addPlotting(self, plotting):
        if plotting not in self.description["tracePlottingList"]:
            self.description["tracePlottingList"].append(plotting)
        
    @property 
    def plottingList(self):
        return self.description["tracePlottingList"]

if __name__=="__main__":
    import sys
    import gc
    t = TraceCollection()
    print(sys.getrefcount(t))
    del t
    gc.collect()
