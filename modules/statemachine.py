# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from collections import defaultdict
from datetime import datetime
import logging
from modules.quantity import Q
import networkx as nx
from functools import partial
# import pygraphviz
from networkx.drawing.nx_agraph import to_agraph


def timedeltaToMagnitude(timedelta):
    return Q((timedelta).total_seconds(), 's')


class StatemachineException(Exception):
    pass


class State(object):
    def __init__(self, name, enterfunc=None, exitfunc=None, now=None, enterObservable=None, exitObservable=None,
                 needsConfirmation=False, confirmedFunc=None):
        self.name = name
        self.enterfunc = enterfunc
        self.exitfunc = exitfunc
        self.enterTime = None
        self.exitTime = None
        self.enterObservable = enterObservable
        self.exitObservable = exitObservable
        self.now = now if now is not None else datetime.now
        self.needsConfirmation = needsConfirmation
        self.confirmedFunc = confirmedFunc
        
    def enterState(self):
        logging.getLogger(__name__).log(25, "Entering state {0}".format(self.name))
        self.enterTime = self.now()
        if self.enterfunc is not None:
            self.enterfunc()
        
    def exitState(self):
        logging.getLogger(__name__).log(25, "Exiting state {0}".format(self.name))
        self.exitTime = self.now()
        if self.exitfunc is not None:
            self.exitfunc()
            
    def timeInState(self):
        return Q( (self.now()-self.enterTime).total_seconds(), 's' )
    
class StateGroup(State):
    def __init__(self, name, states, enterfunc=None, exitfunc=None ):
        super( StateGroup, self ).__init__(name, enterfunc, exitfunc)
        self.states = set(states)


class Transition:
    def __init__(self, fromstate, tostate, condition=None, transitionfunc=None, description=None, eventType=None,
                 refValueFunc=None):
        self.fromstate = fromstate
        self.tostate = tostate
        self.condition = condition if condition is not None else lambda *args: True
        self.transitionfunc = transitionfunc
        self.description = description
        self.refValueFunc = refValueFunc
        self.eventType = eventType

    def transitionState(self, fromObj, toObj):
        if self.transitionfunc is not None:
            self.transitionfunc(fromObj, toObj)
        if self.description is not None:
            if self.refValueFunc is None:
                logging.getLogger(__name__).log(25, "{0} transition {1}".format(self.eventType, self.description))
            else:
                logging.getLogger(__name__).log(25, "{0} transition {1} value {2}".format(self.eventType, self.description, self.refValueFunc()))

class Statemachine:
    def __init__(self, name="Statemachine", now=None ):
        self.states = dict()
        self.transitions = defaultdict( list )
        self.stateGroups = dict()
        self.stateGroupLookup = defaultdict( set )
        self.currentState = None
        self.currentStateReached = True
        self.graph = nx.MultiDiGraph()
        self.name=name
        self.now = now if now is not None else datetime.now
        self.ignoreEventTypes = set()  # these event types are ignored while a state is not confirmed, others are stacked
        self.immediateActionEventTypes = set()  # these event types will be acted upon immediately, independent of the state being reached
        self.eventQueue = list()
        
    def initialize(self, state, enter=True):
        if enter:
            self.states[state].enterState()
        self.currentState = state
        # self.generateDiagram()
                
    def addState(self, name, enterfunc=None, exitfunc=None, needsConfirmation=False, confirmedFunc=None):
        self.states[name] = State( name, enterfunc, exitfunc, now=self.now, needsConfirmation=needsConfirmation,
                                   confirmedFunc=confirmedFunc)
        self.graph.add_node(name)
        
    def addStateGroup(self, name, states, enterfunc=None, exitfunc=None ):
        self.stateGroups[name] = StateGroup( name, states, enterfunc, exitfunc)
        for state in states:
            self.stateGroupLookup[state].add(self.stateGroups[name])
        
    def addStateObj(self, state ):
        self.states[state.name] = state
        
    def addTransition(self, eventType, fromstate, tostate, condition=None, transitionfunc=None, description=None):
        self.addTransitionObj(eventType, Transition(fromstate, tostate, condition, transitionfunc,
                                                    description=description, eventType=eventType))
        
    def addTransitionList(self, eventType, fromstates, tostate, condition=None, description=None):
        for state in fromstates:
            self.addTransitionObj(eventType, Transition(state, tostate, condition, description=description,
                                                        eventType=eventType))
        
    def addTransitionObj(self, eventType, transition):
        if transition.fromstate not in self.states:
            raise StatemachineException("cannot add transition because origin state '{0}' is not defined.".format(transition.fromstate))
        if transition.tostate not in self.states:
            raise StatemachineException("cannot add transition because target state '{0}' is not defined.".format(transition.tostate))
        self.transitions[(eventType, transition.fromstate)].append( transition )
        self.graph.add_edge(transition.fromstate, transition.tostate, label=transition.description )
        
    def makeTransition(self, transition):
        if self.currentState!=transition.fromstate:
            raise StatemachineException("Cannot make transition {0} -> {1} because current state is {2}".format(transition.fromstate, transition.tostate, self.currentState))
        leftStateGroups = self.stateGroupLookup[transition.fromstate] - self.stateGroupLookup[transition.tostate]
        fromStateObj = self.states[transition.fromstate]
        fromStateObj.exitState()
        for stategroup in leftStateGroups:
            stategroup.exitState()
        self.currentState = None
        if fromStateObj.exitObservable is None:
            self._makeTransition_transition(transition)
        else:
            fromStateObj.exitObservable(partial(self._makeTransition_transition, transition))

    def _makeTransition_transition(self, transition):
        fromStateObj = self.states[transition.fromstate]
        toStateObj = self.states[transition.tostate]
        enteredStateGroups = self.stateGroupLookup[transition.tostate] - self.stateGroupLookup[transition.fromstate]
        transition.transitionState(fromStateObj, toStateObj)
        for stategroup in enteredStateGroups:
            stategroup.enterState()
        self.currentStateReached = not toStateObj.needsConfirmation
        if not self.currentStateReached:
            self.confirmationFunction = toStateObj.confirmedFunc
        toStateObj.enterState()
        if toStateObj.enterObservable is None:
            self._makeTransition_enter(transition)
        else:
            toStateObj.enterObservable(partial(self._makeTransition_enter, transition))

    def _makeTransition_enter(self, transition):
        self.currentState = transition.tostate
        logging.getLogger(__name__).debug("Now in state {0}".format(self.currentState))
        
    def processEvent(self, eventType, *args, **kwargs ):
        if self.currentStateReached or eventType in self.immediateActionEventTypes:
            for thistransition in self.transitions[(eventType, self.currentState)]:
                if thistransition.condition( self.states[self.currentState], *args, **kwargs ):
                    logging.getLogger(__name__).debug("Transition initiated by {0} in {1} from {2} to {3}".format(eventType, self.currentState, thistransition.fromstate, thistransition.tostate))
                    self.makeTransition( thistransition )
                    break
        elif eventType not in self.ignoreEventTypes:
            if len(self.eventQueue) < 100:
                self.eventQueue.append((eventType, args, kwargs))
            else:
                logging.getLogger(__name__).debug("Now in state {0}".format(self.currentState))
        return self.currentState

    def confirmStateReached(self):
        self.currentStateReached = True
        if self.confirmationFunction is not None:
            self.confirmationFunction()
            self.confirmationFunction = None

        for eventType, args, kwargs in self.eventQueue:
            self.processEvent(eventType, *args, **kwargs)
        self.eventQueue.clear()


    # def generateDiagram(self):
    #     try:
    #         # convert from networkx -> pydot
    #         pydot_graph = to_agraph(self.graph)
    #
    #         # render pydot by calling dot, no file saved to disk
    #         pydot_graph.graph_attr['overlap']='scale'
    #         pydot_graph.edge_attr.update(fontsize='12', decorate=True)
    #         pydot_graph.layout()
    #         pydot_graph.draw(self.name+".png")
    #         pydot_graph.write(self.name+'.dot')
    #     except:
    #         pass

                
if __name__=="__main__":
    logger = logging.getLogger("")
    logger.setLevel(logging.DEBUG)
    # create console handler with a low log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(levelname)s %(name)s(%(filename)s:%(lineno)d %(funcName)s) %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to logger    
    logger.addHandler(ch)

    sm = Statemachine("Example")
    sm.addState( 'idle', lambda: 1, lambda: 2 )
    sm.addState( 'running', lambda: 3, lambda: 4)
    sm.addState( 'running2', lambda: 5, lambda: 6)
    sm.addState( 'running3', lambda: 7, lambda: 8)
    sm.addState( 'running4', lambda: 9, lambda: 10)
    sm.addStateGroup('group', ['running', 'running2', 'running4'], lambda: 42, lambda: 43)
    sm.addStateGroup('group2', ['running2', 'running3'], lambda: 42, lambda: 43)
    sm.addTransition('runButton', 'idle', 'running', description="runButton")
    sm.addTransitionList('stopButton', ['running', 'running4'], 'idle', description="stopButton")
    sm.addTransition('run2', 'running', 'running2', description="runButton")
    sm.addTransition('run3', 'running2', 'running3', description="runButton")
    sm.addTransition('run4', 'running3', 'running4', description="runButton")
    
    sm.initialize('idle', True)
    sm.processEvent( 'runButton')
    sm.processEvent( 'run2')
    sm.processEvent( 'run3')
    sm.processEvent( 'run4')
    sm.processEvent( 'stopButton')
