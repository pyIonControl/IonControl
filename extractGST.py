import argparse

import os
import pickle

import pygsti
import yaml
from pygsti import report
from pygsti.construction import std1Q_XYI

from trace.TraceCollection import TraceCollection
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def purge_no_timestamp_fron_qubit_data(raw_data):
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


parser = argparse.ArgumentParser(description='Parametrically generate Phoenix geometry')
parser.add_argument('filename', type=str, default=None, nargs='+', help='filename of trace zip')
parser.add_argument('--gst-eval', action='store_true')
parser.add_argument('--save-pickle', action='store_true')
parser.add_argument('--save-txt', action='store_true')
parser.add_argument('--save-yaml', action='store_true')
parser.add_argument('--pickle-protocol', type=int, default=2, help='For python 2.7 use 2; for python 3.5+ use 4')
parser.add_argument('--purge-no-timestamp-from-qubit-data', action='store_true',
                    help='purge results from qubit data for which there is no hardware timestamp')
args = parser.parse_args()

for filename in args.filename:
    folder = os.path.dirname(filename)
    file_base, file_ext = os.path.splitext(os.path.basename(filename))
    Trace = TraceCollection()
    Trace.loadZip(filename)
    qubitData = Trace.structuredData['qubitData']

    if qubitData.is_gst:
        my_gs_target = qubitData.target_gateset
        gs_target = std1Q_XYI.gs_target
        gs_target.spamdefs = my_gs_target.spamdefs
        ds = qubitData.gst_dataset
        output_name = os.path.join(folder, file_base + ".gstdata")
        pygsti.io.write_dataset(output_name, ds, spamLabelOrder=['0', '1'])

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
        generic_data['raw_data'] = {s:dict(r) for s, r in qubitData.data.items()}
        if args.purge_no_timestamp_from_qubit_data:
            purge_no_timestamp_fron_qubit_data(generic_data['raw_data'])
        if args.save_pickle:
            output_name = os.path.join(folder, file_base + ".gstraw.pkl")
            with open(output_name, 'wb') as f:
                pickle.dump(generic_data, f, args.pickle_protocol)
        if args.save_txt:
            output_name = os.path.join(folder, file_base + ".gstraw.txt")
            with open(output_name, 'w') as f:
                print(generic_data, file=f)
        if args.save_yaml:
            output_name = os.path.join(folder, file_base + ".gstraw.yaml")
            with open(output_name, 'w') as f:
                yaml.dump(generic_data, f, Dumper=Dumper)

    if args.gst_eval:
        #gs_target.set_all_parameterizations("TP")
        results = pygsti.do_stdpractice_gst(ds, gs_target, prep_fiducials, meas_fiducials, germs, maxLengths)

        #CHANGE THE OUTPUT FILE FROM OUTPUT.HTML TO WHATEVER YOU WANT, THE TITLE ONLY AFFECTS THE NAME THAT SHOWS UP ON A TAB IN YOUR BROWSER
        pygsti.report.create_general_report(results, filename=os.path.join(folder, file_base + "report.html"),
                                            title=file_base, verbosity=2)

