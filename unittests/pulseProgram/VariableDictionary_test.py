import pickle

from pulseProgram.VariableDictionary import VariableDictionary


def test_pickle_variabledictionary():
    d = VariableDictionary()
    s = pickle.dumps(d)
    dd = pickle.loads(s)
    print(id(dd.dependencyGraph))
