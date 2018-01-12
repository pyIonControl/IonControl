# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging

from networkx import DiGraph, simple_cycles, dfs_postorder_nodes, dfs_preorder_nodes
from networkx import __version__ as nx_version

from modules.Expression import Expression
from modules.SequenceDict import SequenceDict
import copy

if float(nx_version) < 2:
    def nx_indegree_iter(g):
        return g.in_degree_iter()
else:
    def nx_indegree_iter(g):
        return g.in_degree()

class CyclicDependencyException(Exception):
    pass


class VariableDictionaryView(object):
    """View on VariableDictionary that combines the local dictionary with the global dictionary
    the returnvalue is the evaluated value for both dictionaries"""
    def __init__(self, variableDictionary ):
        self.variableDictionary = variableDictionary
        
    def __getitem__(self, key):
        """if the key is in the local dictionary return the value, 
        if it is in the global dictionary return that value,
        otherwise raise KeyError"""
        if key in self.variableDictionary:
            if self.variableDictionary[key].enabled:
                return self.variableDictionary[key].value
            else:
                return self.variableDictionary[key].value * 0  # get zero with the right unit
        if key in self.variableDictionary.globaldict:
            return self.variableDictionary.globaldict.get(key)
        raise KeyError()
    
    def items(self):
        return ((key, var.value if var.enabled else 0 ) for key, var in self.variableDictionary.items())
    
    def __contains__(self, key):
        return key in self.variableDictionary or key in self.variableDictionary.globaldict       
    
 
class VariableDictionary(SequenceDict):
    """Ordered Dictionary to hold variable values. It maintains a dependency graph
    to check for cycles and to recalculate the necessary values when one of the fields is updated"""   
    expression = Expression()
    def __init__(self, *args, **kwargs):
        self.valueView = VariableDictionaryView(self)
        self.dependencyGraph = DiGraph()
        self.globaldict = dict()
        super(VariableDictionary, self).__init__(*args, **kwargs)

    def __getstate__(self):
        return dict((key, value) for key, value in self.__dict__ if key not in ['globaldict'])

    def __setstate__(self, state):
        state.pop('dependencyGraph', None)  # Unpickling of networkx 1.x objects into  networkx 2.x objects fails
        self.__dict__.update(state)

    def __reduce__(self):
        theclass, theitems, inst_dict = super(VariableDictionary, self).__reduce__()
        inst_dict.pop('globaldict', None)
        return theclass, theitems, inst_dict

    def setGlobaldict(self, globaldict):
        self.globaldict = globaldict
        self.calculateDependencies()
                
    def calculateDependencies(self):
        self.dependencyGraph = DiGraph()   # clear the old dependency graph in case parameters got removed
        for name, var in self.items():
            if hasattr(var, 'strvalue'):
                try:
                    var.value, dependencies = self.expression.evaluate(var.strvalue, self.valueView, listDependencies=True)
                    self.addDependencies(self.dependencyGraph, dependencies, name)
                    var.strerror = None
                except (KeyError, ValueError, ZeroDivisionError) as e:
                    logging.getLogger(__name__).warning( str(e) )
                    var.strerror = str(e)
                except Exception as e:
                    errstr = "Unable to evaluate the expression '{0}' for variable '{1}'.".format(var.strvalue,var.name)
                    logging.getLogger(__name__).warning( errstr )
                    var.strerror = errstr
            else:
                var.strerror = None
        self.recalculateAll()
        
    def merge(self, variabledict, globaldict=None, overwrite=False, linkNewToParent=False ):
        if globaldict is not None:
            self.globaldict = globaldict
        for name in list(self.keys()):
            if name not in variabledict:
                self.pop(name)
        for name, var in variabledict.items():
            if var.type in ['parameter', 'address'] and (name not in self or overwrite):
                self[name] = copy.deepcopy(var)
                if linkNewToParent:
                    self[name].useParentValue = True
        self.sortToMatch( list(variabledict.keys()) )        
        self.calculateDependencies()
                
    def __setitem__(self, key, value):
        super(VariableDictionary, self).__setitem__(key, value)
        if hasattr(value, 'strvalue'):
            self.setStrValue( key, value.strvalue )

    def __deepcopy__(self, memo):
        new = type(self)()
        new.globaldict = self.globaldict
        new.update( (name, copy.deepcopy(value)) for name, value in list(self.items()))
        new.dependencyGraph = self.dependencyGraph
        #calculateDependencies()
        return new
                
    def addDependencies(self, graph, dependencies, name):
        """add all the dependencies to name"""
        for dependency in dependencies:
            self.addEdgeNoCycle(graph, dependency, name)        
                
    def addEdgeNoCycle(self, graph, first, second ):
        """add the dependency to the graph, raise CyclicDependencyException in case of cyclic dependencies"""
        graph.add_edge(first, second)
        cycles = simple_cycles( graph )
        for cycle in cycles:
            raise CyclicDependencyException(cycle)
                
    def setStrValueIndex(self, index, strvalue):
        return self.setStrValue( self.keyAt(index), strvalue)
        
    def setStrValue(self, name, strvalue):
        """update the variable value with strvalue and recalculate as necessary"""  
        var = self[name]
        try:
            result, dependencies = self.expression.evaluate(strvalue, self.valueView, listDependencies=True )
            graph = self.dependencyGraph.copy()            # make a copy of the graph. In case of cyclic dependencies we do not want o leave any changes
            for edge in list(graph.in_edges([name])):      # remove all the inedges, dependencies from other variables might be gone
                graph.remove_edge(*edge)
            self.addDependencies(graph, dependencies, name) # add all new dependencies
            var.value = result
            var.strvalue = strvalue
            self.dependencyGraph = graph
            var.strerror = None
        except KeyError as e:
            var.strerror = str(e)
        except Exception as e:
            errstr = "Unable to evaluate the expression '{0}' for variable '{1}'.".format(strvalue,name)
            logging.getLogger(__name__).warning( errstr )
            var.strerror = errstr
        return self.recalculateDependent(name)

    def setParentStrValue(self, name, strvalue):
        var = self[name]
        try:
            result, dependencies = self.expression.evaluate(strvalue, self.valueView, listDependencies=True )
            graph = self.dependencyGraph.copy()            # make a copy of the graph. In case of cyclic dependencies we do not want o leave any changes
            for edge in list(graph.in_edges([name])):      # remove all the inedges, dependencies from other variables might be gone
                graph.remove_edge(*edge)
            self.addDependencies(graph, dependencies, name) # add all new dependencies
            var.parentValue = result
            var.parentStrvalue = strvalue
            self.dependencyGraph = graph
            var.strerror = None
        except KeyError as e:
            var.strerror = str(e)
        except Exception as e:
            errstr = 'Unable to evaluate the expression \'{0}\' for variable \'{1}\'.'.format(strvalue,name)
            logging.getLogger(__name__).warning( errstr )
            var.strerror = errstr
        return self.recalculateDependent(name)

    def setValue(self, name, value):
        """update the variable value with value and recalculate as necessary.
        This is done using existing dependencies."""
        var = self[name]
        try:
            var.value = value
            var.strvalue = ""
            var.strerror = None
        except KeyError as e:
            var.strerror = str(e)
        return self.recalculateDependent(name, returnResult=True)
        
    def setParentValue(self, name, value):
        """update the variable value with value and recalculate as necessary.
        This is done using existing dependencies."""
        var = self[name]
        try:
            var.parentValue = value
            var.parentStrvalue = ""
            var.strerror = None
        except KeyError as e:
            var.strerror = str(e)
        return self.recalculateDependent(name, returnResult=True)

    def setEncodingIndex(self, index, encoding):
        self.at(index).encoding = None if encoding == 'None' else str(encoding)
    
    def setEnabledIndex(self, index, enabled):
        self.at(index).enabled = enabled
       
    def recalculateDependent(self, node, returnResult=False):
        if self.dependencyGraph.has_node(node):
            generator = dfs_preorder_nodes(self.dependencyGraph, node)
            next(generator )   # skip the first, that is us
            nodelist = list(generator)  # make a list, we need it twice 
            result = [ self.recalculateNode(node) for node in nodelist ]                
            return (nodelist, result) if returnResult else nodelist     # return which ones were re-calculated, so gui can be updated 
        return (list(), list()) if returnResult else list()

    def recalculateNode(self, node):
        if node in self:
            var = self[node]
            if hasattr(var, 'strvalue'):
                try:
                    var.value = self.expression.evaluate(var.strvalue, self.valueView)
                    var.strerror = None
                except (KeyError, ValueError) as e:
                    var.strerror = str(e)
                except Exception as e:
                    errstr = 'Unable to evaluate the expression \'{0}\'.'.format(var.strvalue)
                    logging.getLogger(__name__).warning( errstr )
                    var.strerror = errstr
            else:
                logging.getLogger(__name__).warning("variable {0} does not have strvalue. Value is {1}".format(var, var.value))
            return var.value
        return None
            
    def recalculateAll(self):
        g = self.dependencyGraph.reverse()

        # for node, indegree in g.in_degree():
        for node, indegree in nx_indegree_iter(g):  # work around the incompatibility between networkx 1 and 2
            if indegree==0:
                for calcnode in dfs_postorder_nodes(g, node):
                    self.recalculateNode(calcnode)
                    
    def bareDictionaryCopy(self):
        return SequenceDict( self )


if __name__=="__main__":
    class variable:
        def __init__(self, name, strvalue):
            self.strvalue = strvalue
            self.value = 0
            self.type = 'parameter'
            self.name = name
     
    globaldict = { 'G1': 1, 'G2': 8 }
     
    vd = VariableDictionary( { 'L1': variable('L1', 'G1*23+G2'), 'L2': variable('L2', '2*L1'), 'L3': variable('L3', '3*L2+L1') } )
    vd.setGlobaldict( globaldict ) 
    for name, var in vd.items():
        print(name, var.value)
     
    vd.setStrValue('L1', '17*pi')
    print()
    vd.setStrValue('L2', '17*pi')
    print()
    vd.setStrValue('L3', '17*pi')
    print()
    vd.setStrValue('L3', '17*pi*L1+L2')
    print()
    vd.setStrValue('L1', '12')
    print()
    vd.setStrValue('L2', '1')
     
    print(vd.valueView['L1'])
    print(iter(vd.items()))
    
    vd2 = copy.deepcopy(vd)
    vd.setStrValue('L2', '7')
    
    print(list(vd.items()))
    print(list(vd2.items()))
    print(vd['L2'].value)
    print(vd2['L2'].value)
    
    import pickle
    s = pickle.dumps(vd, 0)
    vc = pickle.loads(s)
    print('unpickled', vc)
    print(vc.at(1))
    
  
    