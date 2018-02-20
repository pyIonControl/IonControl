import argparse
import hashlib

import os
import pickle
from pathlib import Path
import datetime
from datetime import timezone

import pygsti
import yaml
from pygsti import report
from pygsti.construction import std1Q_XYI
from objecthash import Hasher

from trace.TraceCollection import TraceCollection
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def separate_no_timestamp_from_qubit_data(raw_data):
    for record in raw_data.values():
        repeats = record['repeats']
        timestamps = record['timestamps']
        value = record['value']
        new_repeats = list()
        new_timestamps = list()
        new_value = list()
        drift_repeats = list()
        drift_timestamps = list()
        drift_value = list()
        for r, t, v in zip(repeats, timestamps, value):
            if isinstance(t, int):
                new_repeats.append(r)
                new_timestamps.append(t)
                new_value.append(v)
            else:
                drift_repeats.append(r)
                drift_timestamps.append(t)
                drift_value.append(v)
        record['repeats'] = new_repeats
        record['timestamps'] = new_timestamps
        record['value'] = new_value
        record['_drift_repeats'] = drift_repeats
        record['_drift_timestamps'] = drift_timestamps
        record['_drift_value'] = drift_value


def copy_to_GST_data(raw_data, name):
    for record in raw_data.values():
        record['repeats'] = record['_' + name + "_repeats"]
        record['timestamps'] = record['_' + name + "_timestamps"]
        record['value'] = record['_' + name + "_value"]


def fix_timestamps(qubit_data, offset, scaling=5):
    d = qubit_data._rawdata
    min_ts = 2**64
    max_ts = 0
    min_fts = 1e12
    max_fts = 0
    for v in d.values():
        ts = v.get('timestamps')
        if ts and isinstance(ts[0], int):
            v['timestamps'] = [t * scaling + offset for t in ts]
            min_ts = min(min_ts, min(v['timestamps']))
            max_ts = max(max_ts, max(v['timestamps']))
        for key, value in v.items():
            if key.endswith("_ts") and value:
                if isinstance(value[0], int):
                    value[:] = [t * scaling + offset for t in value]
                    min_ts = min(min_ts, min(value))
                    max_ts = max(max_ts, max(value))
                else:
                    min_fts = min(min_fts, min(value))
                    max_fts = max(max_fts, max(value))
    deviation = (min_ts*1e-9 - min_fts)/(2**40*5e-9)
    if abs(deviation > 0.001):
        print("Timestamp difference: {} overflows --- correcting".format(deviation))
        return fix_timestamps(qubit_data, int(-min_ts + min_fts*1e9), 1)
    return min_ts, max_ts

parser = argparse.ArgumentParser(description='Parametrically generate Phoenix geometry')
parser.add_argument('filename', type=str, default=None, nargs='+', help='filename of trace zip')
parser.add_argument('--gst-eval', action='store_true')
parser.add_argument('--save-pickle', action='store_true')
parser.add_argument('--save-txt', action='store_true')
parser.add_argument('--save-yaml', action='store_true')
parser.add_argument('--length-exp', type=str, default=None, help='GST maximum length exponent e.g. 10 for 1024')
parser.add_argument('--path', type=str, default=None, help='prepend path for all files')
parser.add_argument('--pickle-protocol', type=int, default=2, help='For python 2.7 use 2; for python 3.5+ use 4')
parser.add_argument('--separate-no-timestamp-from-qubit-data', action='store_true',
                    help='purge results from qubit data for which there is no hardware timestamp')
parser.add_argument('--copy-to-GST-data', type=str, default=None,
                    help='copy data from evaluation to GST data')
args = parser.parse_args()

commonPath = Path(args.path)
filename = args.filename[0]
filename = commonPath / filename
folder = filename.parent
Trace = TraceCollection()
Trace.loadZip(str(filename))
qubitData = Trace.structuredData['qubitData']
time_offset = int(Trace.description.get('timeTickOffset', 0) * 1e9)
if time_offset:
    mi, ma = fix_timestamps(qubitData, time_offset)
    print(args.filename[0], round((ma-mi)*1e-9, 6), "s")
for otherfilename in args.filename[1:]:
    otherTrace = TraceCollection()
    otherTrace.loadZip(str(commonPath / otherfilename))
    qd = otherTrace.structuredData['qubitData']
    time_offset = int(otherTrace.description.get('timeTickOffset', 0) * 1e9)
    if time_offset:
        mi, ma = fix_timestamps(qd, time_offset)
        print(otherfilename, round((ma-mi)*1e-9, 6), "s")
    qubitData.update(qd)

my_gs_target = qubitData.target_gateset
gs_target = std1Q_XYI.gs_target
gs_target.preps = my_gs_target.preps
gs_target.povms = my_gs_target.povms
ds = qubitData.gst_dataset
germs = std1Q_XYI.germs
prep_fiducials = std1Q_XYI.prepStrs
meas_fiducials = std1Q_XYI.effectStrs
if args.length_exp is not None:
    exponent = int(args.length_exp)
    maxLengths = [1<<i for i in range(exponent+1)]

if qubitData.is_gst:
    output_name = filename.with_suffix(".gstdata")
    pygsti.io.write_dataset(str(output_name), ds, outcomeLabelOrder=['0', '1'])

    #Create germ gate string lists
    germs = qubitData.germs or std1Q_XYI.germs
    prep_fiducials = qubitData.prepFiducials or std1Q_XYI.prepStrs
    meas_fiducials = qubitData.measFiducials or std1Q_XYI.effectStrs

    #Create maximum lengths list
    maxLengths = qubitData.maxLengths or [1,2,4,8,16,32,64,128,256,512,1024]

if args.save_pickle or args.save_txt or args.save_yaml:
    generic_data = dict()
    generic_data['target_gateset'] = qubitData.target_gateset
    if qubitData.is_gst:
        generic_data['gst_dataset'] = qubitData.gst_dataset
    generic_data['gatestring_list'] = qubitData.gatestring_list
    generic_data['max_lengths'] = qubitData.maxLengths
    generic_data['meas_fiducials'] = qubitData.measFiducials
    generic_data['prep_fiducials'] = qubitData.prepFiducials
    generic_data['germs'] = qubitData.germs
    if args.separate_no_timestamp_from_qubit_data:
        separate_no_timestamp_from_qubit_data(qubitData.data)
        ds = qubitData.gst_dataset
    generic_data['raw_data'] = {s:dict(r) for s, r in qubitData.data.items()}
    if args.save_pickle:
        output_name = filename.with_suffix(".gstraw.pkl")
        with open(str(output_name), 'wb') as f:
            pickle.dump(generic_data, f, args.pickle_protocol)
    if args.save_txt:
        output_name = filename.with_suffix(".gstraw.txt")
        with open(str(output_name), 'w') as f:
            print(generic_data, file=f)
    if args.save_yaml:
        output_name = filename.with_suffix(".gstraw.yaml")
        with open(str(output_name), 'w') as f:
            yaml.dump(generic_data, f, Dumper=Dumper)

if args.copy_to_GST_data:
    copy_to_GST_data(qubitData.data, args.copy_to_GST_data)
    ds = qubitData.gst_dataset

if args.gst_eval:
    #if qubitData.is_gst:
        #gs_target.set_all_parameterizations("TP")
    results = pygsti.do_stdpractice_gst(ds, gs_target, prep_fiducials, meas_fiducials, germs, maxLengths)

        #CHANGE THE OUTPUT FILE FROM OUTPUT.HTML TO WHATEVER YOU WANT, THE TITLE ONLY AFFECTS THE NAME THAT SHOWS UP ON A TAB IN YOUR BROWSER
    pygsti.report.create_standard_report(results, filename=str(filename.with_suffix(".html")),
                                            title=filename.stem, verbosity=2)
    # else:
    #     print("This claims to be not GST data, not running the evaluation")

