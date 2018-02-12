import grpc
from externalParameter.labbricksproto_pb2_grpc import LabbricksStub
from externalParameter.labbricksproto_pb2 import DeviceRequest, DeviceSetIntRequest

channel = grpc.insecure_channel('localhost:50051')
stub = LabbricksStub(channel)

r = DeviceRequest()

for info in stub.DeviceInfo(r):
    print(info)

r = DeviceSetIntRequest()
r.ModelName = "LMS-123"
r.SerialNumber = 200123
r.Data = 900000000
print(stub.SetFrequency(r))