from collections import defaultdict

import numpy
import pygsti


class QubitResultContainer(dict):
    def __missing__(self, key):
        ret = self[key] = QubitResult()
        return ret

    def update(self, other):
        for key, value in other.items():
            self[key].update(value)


class QubitResult(dict):
    def __missing__(self, key):
        ret = self[key] = list()
        return ret

    def update(self, other):
        for key, value in other.items():
            self[key].extend(value)


class ResultCounter(dict):
    def __init__(self, values, repeats, keys=[], force_string=False):
        super().__init__({k: 0 for k in keys})
        if force_string:
            for v, r in zip(values, repeats):
                self[str(v)] += r
        else:
            for v, r in zip(values, repeats):
                self[v] += r


    def __missing__(self, key):
        ret = self[key] = 0
        return ret


class QubitDataSet:
    _fields = ['gatestring_list', 'plaquettes', 'target_gateset', '_rawdata', 'prepFiducials', 'measFiducials',
               'germs', 'maxLengths']
    def __init__(self, gatestring_list=None, plaquettes=None, target_gateset=None,
                 prepFiducials=None, measFiducials=None, germs=None, maxLengths=None):
        self.gatestring_list = gatestring_list
        self.gatestring_dict = {s: idx for idx, s in enumerate(gatestring_list)} if gatestring_list else None
        self.plaquettes = plaquettes
        self.target_gateset = target_gateset
        self._rawdata = QubitResultContainer()  # _rawdata[gatestring]['value' 'repeats' 'timestamps' ...] list
        self.prepFiducials = prepFiducials
        self.measFiducials = measFiducials
        self.maxLengths = maxLengths
        self.germs = germs
        self._init_internal()

    def _init_internal(self):
        if self.is_gst:
            self.spam_labels = ['0', '1']  # self.target_gateset.get_spam_labels()
            self._countVecMx = numpy.zeros((len(self.spam_labels), len(self.gatestring_list)), 'd')
            self._totalCntVec = numpy.zeros(len(self.gatestring_list), 'd')
            for gatestring, d in self._rawdata.items():
                self._extend(gatestring, d['value'], d['repeats'])
        else:
            self._countVecMx = None
            self._totalCntVec = None
            self.spam_labels = None

    def update(self, other):
        if self.gatestring_list != other.gatestring_list:
            raise AttributeError("gatestring_lists do not match")
        self._rawdata.update(other._rawdata)

    def __getstate__(self):
        return {key: getattr(self, key) for key in self._fields}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__dict__.setdefault('prepFiducials', None)
        self.__dict__.setdefault('measFiducials', None)
        self.__dict__.setdefault('germs', None)
        self.__dict__.setdefault('maxLengths', None)
        self.gatestring_dict = {s: idx for idx, s in enumerate(self.gatestring_list)} if self.gatestring_list else None
        self._init_internal()

    def extend(self, gatestring, evaluation, add_to_color_box_plot, values, repeats, timestamps):
        """Append the measurement result for gatestring to the datastructure"""
        point = self._rawdata[gatestring]
        if add_to_color_box_plot:
            point['value'].extend(values)
            point['repeats'].extend(repeats)
            point['timestamps'].extend(timestamps)
            self._extend(gatestring, values, repeats)
        else:
            point['_' + evaluation + "_value"].extend(values)
            point['_' + evaluation + '_repeats'].extend(repeats)
            point['_' + evaluation + '_timestamps'].extend(timestamps)

    def _extend(self, gatestring, values, repeats):
        """Keeps the data in the input format for pygsti log_likelyhood up to date"""
        if self.is_gst:
            gatestring_idx = self.gatestring_dict[gatestring]
            if len(values) == 1:
                v, r = next(iter(values)), next(iter(repeats))
                self._countVecMx[self.spam_labels.index(str(v)), gatestring_idx] += r
                self._totalCntVec[gatestring_idx] += r
            else:
                # print("len(values)", len(values))
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
        return self.gatestring_list is not None and self.target_gateset is not None and self.plaquettes is not None

    def __eq__(self, other):
        return (isinstance(other, QubitDataSet) and
                all(getattr(self, f) == getattr(other, f) for f in ('gatestring_list', '_rawdata')))

    @property
    def gst_dataset(self):
        ds = pygsti.objects.DataSet(outcomeLabels=['0', '1'])
        for gs, data in self.data.items():
            rc = ResultCounter(data['value'], data['repeats'], keys=['0', '1'],
                               force_string=True)
            ds.add_count_dict(gs, rc)
        ds.done_adding_data()
        return ds

