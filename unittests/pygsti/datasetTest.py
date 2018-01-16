import pygsti
from pygsti.construction import std1Q_XYI


def test_dataset():

    # Depolarize the perfect X,Y,I gate set
    depol_gateset = std1Q_XYI.gs_target.depolarize(gate_noise=0.1)

    # Compute the sequences needed to perform Long Sequence GST on
    # this GateSet with sequences up to lenth 512
    gatestring_list = pygsti.construction.make_lsgst_experiment_list(
        std1Q_XYI.gs_target, std1Q_XYI.prepStrs, std1Q_XYI.effectStrs,
        std1Q_XYI.germs, [1, 2, 4, 8, 16, 32, 64, 128, 256, 512])

    # Generate fake data (Tutorial 00)
    ds3 = pygsti.construction.generate_fake_data(depol_gateset, gatestring_list, nSamples=1000,
                                                 sampleError='binomial', seed=100)
    ds3b = pygsti.construction.generate_fake_data(depol_gateset, gatestring_list, nSamples=50,
                                                  sampleError='binomial', seed=100)
    pass
