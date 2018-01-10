import yaml
from pygsti.objects import GateString
from pygsti.objects.gatestringstructure import GatestringPlaquette

from pygsti_addons.QubitDataSet import QubitDataSet, QubitResultContainer, QubitResult, ResultCounter


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
    yield qubit_data_set
    qubit_data_set.__setstate__(state)

yaml.add_representer(QubitDataSet, _QubitDataSet_representer)
yaml.add_constructor('!QubitDataSet', _QubitDataSet_constructor)


def make_custom_mapping(cls, node_name):
    def _cls_representer(dumper, d):
        return dumper.represent_mapping(node_name, d)

    def _cls_loader(loader, data):
        result = cls()
        mapping = loader.construct_mapping(data)
        yield result
        result.update(mapping)

    yaml.add_representer(cls, _cls_representer)
    yaml.add_constructor(node_name, _cls_loader)

make_custom_mapping(QubitResultContainer, '!QubitResultContainer')
make_custom_mapping(QubitResult, '!QubitResult')
make_custom_mapping(ResultCounter, '!ResultCounter')

