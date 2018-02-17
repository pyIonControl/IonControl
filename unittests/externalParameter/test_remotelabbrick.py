import pytest
import socket

from externalParameter.RemoteLabBrick import RemoteLabBrick, Servers, RemoteLabBrickConfig


def test_collectInormation():
    hostname = socket.gethostname()
    Servers['local'] = RemoteLabBrickConfig(hostname, hostname + ':50051', True, hostname + ".key", hostname + ".crt", "ca.crt")
    instruments = RemoteLabBrick.collectInformation()
    assert len(instruments) > 0

def test_instrument():
    hostname = socket.gethostname()
    Servers['local'] = RemoteLabBrickConfig(hostname, hostname + ':50051', True, hostname + ".key", hostname + ".crt", "ca.crt")
    devices = RemoteLabBrick.collectInformation()
    identifier = '_'.join(map(str, next(iter(devices.keys()))))
    inst = RemoteLabBrick(identifier)
    targetPower = (inst.minPower + inst.maxPower) / 2
    inst.power = targetPower
    assert inst.power == targetPower
