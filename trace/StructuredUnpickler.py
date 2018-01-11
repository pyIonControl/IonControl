import pickle
from collections import OrderedDict

from pygsti.objects.labeldicts import OrderedMemberDict


class OrderedSPAMLabelDict(OrderedDict):
    def __init__(self, remainderLabel, items=[]):
        super(OrderedSPAMLabelDict, self).__init__(items)

class OrderedGateDict(OrderedMemberDict):
    """ Dummy """
    def __init__(self, parent, default_param, prefix, items=[]):
        OrderedMemberDict.__init__(self, parent, default_param, prefix, "gate", items)

class OrderedSPAMVecDict(OrderedMemberDict):
    """ Dummy """
    def __init__(self, parent, default_param, remainderLabel, prefix, items=[]):
        OrderedMemberDict.__init__(self, parent, default_param, prefix, "spamvec", items)


_backward_compatibility_map = {
    ('pygsti.tools.basis', 'Basis'): ('pygsti.baseobjs', 'Basis'),
    ('pygsti.tools.dim', 'Dim'): ('pygsti.baseobjs', 'Dim'),
    ('pygsti.objects.labeldicts', 'OrderedSPAMLabelDict'): ('trace.StructuredUnpickler', 'OrderedSPAMLabelDict'),
    ('pygsti.objects.labeldicts', 'OrderedSPAMVecDict'): ('trace.StructuredUnpickler', 'OrderedSPAMVecDict'),
    ('pygsti.objects.labeldicts', 'OrderedGateDict'): ('trace.StructuredUnpickler', 'OrderedGateDict')}



class StructuredUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        # print("find_class({}, {})".format(module, name))
        if (module, name) in _backward_compatibility_map:
            return super(StructuredUnpickler, self).find_class(*_backward_compatibility_map[(module, name)])
        return super(StructuredUnpickler, self).find_class(module, name)