import grpc
from externalParameter.labbricksproto_pb2_grpc import LabbricksStub
from externalParameter.labbricksproto_pb2 import DeviceRequest, DeviceSetIntRequest

creds = grpc.ssl_channel_credentials(root_certificates=open('ca.crt', 'rb').read(),
                                     private_key=open('client.key', 'rb').read(),
                                     certificate_chain=open('client.crt', 'rb').read())

channel = grpc.secure_channel('thinker:50051', creds)
stub = LabbricksStub(channel)

r = DeviceRequest()

for info in stub.DeviceInfo(r):
    print(info)

# for info in stub.DeviceNotifications(r):
#     print(info)

r = DeviceSetIntRequest()
r.ModelName = "LMS-123"
r.SerialNumber = 200123
r.Data = 900000000
print(stub.SetFrequency(r))

f = stub.SetFrequency.future(r)
print(f.result())

f = stub.DeviceNotifications.future_stream(r)