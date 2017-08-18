import pygsti
from pygsti import report
from pygsti.construction import std1Q_XYI

from trace.TraceCollection import TraceCollection

Trace = TraceCollection()
Trace.loadZip(r'C:\Users\plmaunz\Documents\170807\GSTScan_057.zip')
qubitData = Trace.structuredData['qubitData']
ds = qubitData.gst_dataset
my_gs_target = qubitData.target_gateset
gs_target = std1Q_XYI.gs_target
gs_target.spamdefs = my_gs_target.spamdefs


pygsti.io.write_dataset(r'C:\Users\plmaunz\Documents\170807\GSTScan_057_qubitdata.txt', ds, spamLabelOrder=['0', '1'])

#Create fiducial gate string lists
fiducials = pygsti.construction.gatestring_list( [ (), ('Gx',), ('Gy',), ('Gx','Gx'), ('Gx','Gx','Gx'), ('Gy','Gy','Gy') ])

#Create germ gate string lists
germs = pygsti.construction.gatestring_list( [('Gx',), ('Gy',), ('Gi',), ('Gx', 'Gy',),
         ('Gx', 'Gy', 'Gi',), ('Gx', 'Gi', 'Gy',), ('Gx', 'Gi', 'Gi',), ('Gy', 'Gi', 'Gi',),
         ('Gx', 'Gx', 'Gi', 'Gy',), ('Gx', 'Gy', 'Gy', 'Gi',),
         ('Gx', 'Gx', 'Gy', 'Gx', 'Gy', 'Gy',)] )

prep_fiducials, meas_fiducials = std1Q_XYI.prepStrs, std1Q_XYI.effectStrs
germs = std1Q_XYI.germs

#Create maximum lengths list
maxLengths = [1,2,4,8,16,32,64,128,256,512,1024]

#gs_target.set_all_parameterizations("TP")
results = pygsti.do_stdpractice_gst(ds, gs_target, prep_fiducials, meas_fiducials, germs, maxLengths)
pygsti.report.create_general_report(results, filename=r'C:\Users\plmaunz\Documents\170807\GSTScan_057.html',
                                    title="GSTScan_057", verbosity=2)