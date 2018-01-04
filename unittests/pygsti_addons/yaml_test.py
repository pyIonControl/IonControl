import unittest
from math import sqrt
import yaml
import pickle

import numpy
from pygsti.objects import GateSet
import pygsti_addons.yaml as _yaml


class TestYaml(unittest.TestCase):
    def test_gateset_file(self):
        # Initialize an empty GateSet object
        gateset1 = GateSet()

        # Populate the GateSet object with states, effects, gates,
        # all in the *normalized* Pauli basis: { I/sqrt(2), X/sqrt(2), Y/sqrt(2), Z/sqrt(2) }
        # where I, X, Y, and Z are the standard Pauli matrices.
        gateset1['rho0'] = [1 / sqrt(2), 0, 0, 1 / sqrt(2)]  # density matrix [[1, 0], [0, 0]] in Pauli basis
        gateset1['E0'] = [1 / sqrt(2), 0, 0, -1 / sqrt(2)]  # projector onto [[0, 0], [0, 1]] in Pauli basis
        gateset1['Gi'] = numpy.identity(4, 'd')  # 4x4 identity matrix
        gateset1['Gx'] = [[1, 0, 0, 0],
                          [0, 1, 0, 0],
                          [0, 0, 0, -1],
                          [0, 0, 1, 0]]  # pi/2 X-rotation in Pauli basis

        gateset1['Gy'] = [[1, 0, 0, 0],
                          [0, 0, 0, 1],
                          [0, 0, 1, 0],
                          [0, -1, 0, 0]]  # pi/2 Y-rotation in Pauli basis

        # Create SPAM labels "plus" and "minus" using the special "remainder" label,
        # and set the then-needed identity vector.
        gateset1.spamdefs['1'] = ('rho0', 'E0')
        gateset1.spamdefs['0'] = ('rho0', 'remainder')
        gateset1['identity'] = [sqrt(2), 0, 0, 0]  # [[1, 0], [0, 1]] in Pauli basis

        s = yaml.dump(gateset1)
        g2 = yaml.load(s)
        self.assertEqual(gateset1.jtracedist(g2), 0)

        s = yaml.dump(gateset1).encode()
        g2 = yaml.load(s.decode())
        self.assertEqual(gateset1.jtracedist(g2), 0)

        with open('temp.bin', 'wb') as f:
            f.write(yaml.dump(gateset1).encode())
        with open('temp.bin', 'rb') as f:
            g2 = yaml.load(f.read().decode())
        self.assertEqual(gateset1.jtracedist(g2), 0)

    def test_data_read_write(self):
        with open('qubitData.pkl', 'rb') as f:
            data = pickle.load(f)
        s = yaml.dump(data).encode()
        data_4 = yaml.load(s.decode())
        r = data == data_4
        self.assertTrue(r)



if __name__ == "__main__":
    unittest.main()
