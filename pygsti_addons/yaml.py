import yaml
from pygsti.objects import GateString
from pygsti.objects.gatestringstructure import GatestringPlaquette

from pygsti_addons.QubitDataSet import QubitDataSet


def _GateString_representer(dumper, gate_string):
    return dumper.represent_scalar('!GateString', str(gate_string))


def _GateString_constructor(loader, node):
    return GateString(None, loader.construct_scalar(node))


yaml.add_representer(GateString, _GateString_representer)
yaml.add_constructor('!GateString', _GateString_constructor)


_plaquette_keys = ['base', 'rows', 'cols', 'elements', 'aliases']


def _GateStringPlaquette_representer(dumper, gate_string_plaquette):
    return dumper.represent_mapping('!GateStringPlaquette', {key: getattr(gate_string_plaquette, key) for key in _plaquette_keys})


def _GateStringPlaquette_constructor(loader, node):
    data = loader.construct_mapping(node)
    return GatestringPlaquette(**data)


yaml.add_representer(GatestringPlaquette, _GateStringPlaquette_representer)
yaml.add_constructor('!GateStringPlaquette', _GateStringPlaquette_constructor)


def _QubitDataSet_representer(dumper, qubit_data_set):
    return dumper.represent_mapping('!QubitDataSet', qubit_data_set.__getstate__())

def _QubitDataSet_constructor(loader, node):
    qubit_data_set = QubitDataSet()
    state = loader.construct_mapping(node)
    qubit_data_set.__setstate__(state)
    return qubit_data_set

yaml.add_representer(QubitDataSet, _QubitDataSet_representer)
yaml.add_constructor('!QubitDataSet', _QubitDataSet_constructor)

