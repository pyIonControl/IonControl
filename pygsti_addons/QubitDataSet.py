from collections import defaultdict

import numpy


def qubitDataStructure():
    return defaultdict(list)


class ResultCounter(dict):
    def __init__(self, values, repeats):
        super().__init__()
        for v, r in zip(values, repeats):
            self[v] += r

    def __missing__(self, key):
        ret = self[key] = 0
        return ret


class QubitDataSet:
    _fields = ['gatestring_list', 'plaquettes', 'target_gateset', '_rawdata']
    def __init__(self, gatestring_list=None, plaquettes=None, target_gateset=None):
        self.gatestring_list = gatestring_list
        self.plaquettes = plaquettes
        self.target_gateset = target_gateset
        self._rawdata = defaultdict(qubitDataStructure)  # _rawdata[gatestring]['value' 'repeats' 'timestamps' ...] list
        self._init_internal()

    def _init_internal(self):
        if self.is_gst:
            self.spam_labels = self.target_gateset.get_spam_labels()
            self._countVecMx = numpy.zeros((len(self.spam_labels), len(self.gatestring_list)), 'd')
            self._totalCntVec = numpy.zeros(len(self.gatestring_list), 'd')
            for gatestring, d in self._rawdata.items():
                self._extend(gatestring, d['value'], d['repeats'])
        else:
            self._countVecMx = None
            self._totalCntVec = None

    def __getstate__(self):
        return {key: getattr(self, key) for key in self._fields}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._init_internal()

    def extend(self, gatestring, values, repeats, timestamps):
        """Append the measurement result for gatestring to the datastructure"""
        point = self._rawdata[gatestring]
        point['value'].extend(values)
        point['repeats'].extend(repeats)
        point['timestamps'].extend(timestamps)
        self._extend(gatestring, values, repeats)

    def _extend(self, gatestring, values, repeats):
        """Keeps the data in the input format for pygsti log_likelyhood up to date"""
        if self.is_gst:
            gatestring_idx = self.gatestring_list.index(gatestring)
            eval = ResultCounter(values, repeats)
            for label, count in eval.items():
                self._countVecMx[self.spam_labels.index(str(label)), gatestring_idx] += count
            self._totalCntVec[gatestring_idx] += sum(eval.values())

    def extendEnv(self, gatestring, name, values, timestamps):
        if values and timestamps:
            point = self._rawdata[gatestring]
            point['_' + name].extend(values)
            point['_' + name + '_ts'].extend(timestamps)

    @property
    def countVecMx(self):
        return self._countVecMx

    @property
    def totalCntVec(self):
        return self._totalCntVec

    @property
    def data(self):
        return self._rawdata

    @property
    def is_gst(self):
        return self.gatestring_list is not None and self.target_gateset is not None




