import argparse

import os
import pygsti
from pygsti import report
from pygsti.construction import std1Q_XYI

from trace.TraceCollection import TraceCollection

parser = argparse.ArgumentParser(description='Parametrically generate Phoenix geometry')
parser.add_argument('filename', type=str, default=None, nargs='+', help='filename of trace zip')
args = parser.parse_args()

for filename in args.filename:
    folder = os.path.dirname(filename)
    file_base, file_ext = os.path.splitext(os.path.basename(filename))
    Trace = TraceCollection()
    Trace.loadZip(filename)
    qubitData = Trace.structuredData['qubitData']
    ds = qubitData.gst_dataset
    my_gs_target = qubitData.target_gateset
    gs_target = std1Q_XYI.gs_target
    gs_target.spamdefs = my_gs_target.spamdefs

    output_name = os.path.join(folder, file_base + ".gstdata")
    pygsti.io.write_dataset(output_name, ds, spamLabelOrder=['0', '1'])

    #Create germ gate string lists
    germs = qubitData.germs or std1Q_XYI.germs
    prep_fiducials = qubitData.prepFiducials or std1Q_XYI.prepStrs
    meas_fiducials = qubitData.measFiducials or std1Q_XYI.effectStrs

    #Create maximum lengths list
    maxLengths = qubitData.maxLengths or [1,2,4,8,16,32,64,128,256,512,1024]

    #gs_target.set_all_parameterizations("TP")
    results = pygsti.do_stdpractice_gst(ds, gs_target, prep_fiducials, meas_fiducials, germs, maxLengths)

    #CHANGE THE OUTPUT FILE FROM OUTPUT.HTML TO WHATEVER YOU WANT, THE TITLE ONLY AFFECTS THE NAME THAT SHOWS UP ON A TAB IN YOUR BROWSER
    pygsti.report.create_general_report(results, filename=r'{}'.format(os.path.join(folder, file_base + "report.html")),
                                        title="GSTScan_057", verbosity=2)