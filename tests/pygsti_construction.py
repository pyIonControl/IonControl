import numpy
import pygsti
import pygsti.construction as pc
from pygsti.objects import GateSet, GateString
from pygsti_addons import yaml as _yaml
from pygsti import logl, logl_max, logl_terms, logl_max_terms
import yaml

from math import sqrt
import numpy as np

#Initialize an empty GateSet object
gateset1 = GateSet()

#Populate the GateSet object with states, effects, gates,
# all in the *normalized* Pauli basis: { I/sqrt(2), X/sqrt(2), Y/sqrt(2), Z/sqrt(2) }
# where I, X, Y, and Z are the standard Pauli matrices.
gateset1['rho0'] = [ 1/sqrt(2), 0, 0, 1/sqrt(2) ] # density matrix [[1, 0], [0, 0]] in Pauli basis
gateset1['E0'] = [ 1/sqrt(2), 0, 0, -1/sqrt(2) ]  # projector onto [[0, 0], [0, 1]] in Pauli basis
gateset1['Gi'] = np.identity(4,'d') # 4x4 identity matrix
gateset1['Gx'] = [[1, 0, 0, 0],
                  [0, 1, 0, 0],
                  [0, 0, 0,-1],
                  [0, 0, 1, 0]] # pi/2 X-rotation in Pauli basis

gateset1['Gy'] = [[1, 0, 0, 0],
                  [0, 0, 0, 1],
                  [0, 0, 1, 0],
                  [0,-1, 0, 0]] # pi/2 Y-rotation in Pauli basis

#Create SPAM labels "plus" and "minus" using the special "remainder" label,
# and set the then-needed identity vector.
gateset1.spamdefs['1'] = ('rho0','E0')
gateset1.spamdefs['0'] = ('rho0','remainder')
gateset1['identity'] = [ sqrt(2), 0, 0, 0 ]  # [[1, 0], [0, 1]] in Pauli basis

pygsti.io.write_gateset(gateset1, "tutorial_files/MyTargetGateset.txt")


#Create fiducial gate string lists
fiducials = pygsti.construction.gatestring_list( [ (), ('Gx',), ('Gy',), ('Gx','Gx'), ('Gx','Gx','Gx'), ('Gy','Gy','Gy') ])

#Create germ gate string lists
germs = pygsti.construction.gatestring_list( [('Gx',), ('Gy',), ('Gi',), ('Gx', 'Gy',),
         ('Gx', 'Gy', 'Gi',), ('Gx', 'Gi', 'Gy',), ('Gx', 'Gi', 'Gi',), ('Gy', 'Gi', 'Gi',),
         ('Gx', 'Gx', 'Gi', 'Gy',), ('Gx', 'Gy', 'Gy', 'Gi',),
         ('Gx', 'Gx', 'Gy', 'Gx', 'Gy', 'Gy',)] )

#Create maximum lengths list
maxLengths = [1,2,4,8,16,32,64,128,256,512,1024]

pygsti.io.write_gatestring_list("tutorial_files/MyFiducials.txt", fiducials, "My fiducial gate strings")
pygsti.io.write_gatestring_list("tutorial_files/MyGerms.txt", germs, "My germ gate strings")

listOfExperimentsStruct = pygsti.construction.make_lsgst_structs(gateset1.gates.keys(),
                                                                   fiducials, fiducials, germs, maxLengths, nest=True)[-1]
# myset = dict((ex, idx) for idx, ex in enumerate(listOfExperiments))

lengths = sorted(set([k[0] for k in listOfExperimentsStruct._plaquettes.keys()]))
germs = sorted(set([k[1] for k in listOfExperimentsStruct._plaquettes.keys()]))

d = dict()
for (l, g), p in listOfExperimentsStruct._plaquettes.items():
    l_id = lengths.index(l)
    g_id = germs.index(g)
    for r, c, s in p:
        d[s] = (l_id, g_id, c, r)

listOfExperiments = listOfExperimentsStruct.allstrs

#Create an empty dataset file, which stores the list of experiments
#plus extra columns where data can be inserted
pygsti.io.write_empty_dataset("tutorial_files/MyDataTemplate.txt", listOfExperiments,
                              "## Columns = plus count, count total")

print(yaml.dump(GateString(None, 'Gx^2')))
print(yaml.dump(listOfExperimentsStruct._plaquettes))

result = gateset1.product(GateString(None, 'Gx'))
probs = gateset1.probs(GateString(None, 'Gx^2'))
print(probs)

evaltree = gateset1.bulk_evaltree(listOfExperiments)
bulk_probs = gateset1.bulk_probs(evaltree)
print(bulk_probs)

spamLabels = gateset1.get_spam_labels() #this list fixes the ordering of the spam labels
spam_lbl_rows = {sl: i for (i, sl) in enumerate(spamLabels)}

probs = numpy.empty((len(spamLabels), len(listOfExperiments)), 'd')
gateset1.bulk_fill_probs(probs, spam_lbl_rows, evaltree, (-1e6,1e6))

gs_datagen = gateset1.depolarize(gate_noise=0.00001, spam_noise=0.000)
ds = pygsti.construction.generate_fake_data(gs_datagen, listOfExperiments, nSamples=1000,
                                            sampleError="binomial") # , seed=2015)

countVecMx = numpy.empty( (len(spamLabels),len(listOfExperiments)), 'd' )
pygsti.fill_count_vecs(countVecMx, spam_lbl_rows, ds, listOfExperiments)
totalCntVec = numpy.array( [ds[gstr].total() for gstr in listOfExperiments], 'd')


import time
print("Start")
t_start = time.time()
ll = logl_terms(gateset1, ds, evalTree=evaltree, probs=probs, countVecMx=countVecMx, totalCntVec=totalCntVec)
lmax = logl_max_terms(ds)
#print(numpy.sum(2 * (lmax - ll), axis=0))
dof = len(ll[0])

#ll = logl(gateset1, ds)
#lmax = logl_max(ds)
print(2 * (lmax - ll) / dof)

print("Duration {}".format(time.time() - t_start))
