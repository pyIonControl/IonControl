import pytest
from influxdb import InfluxDBClient

# add ca.crt to C:\WinPython-64bit-3.5.4.0Qt5\python-3.5.4.amd64\Lib\site-packages\certifi\cacert.pem

# def test_influx_ssl():
#     host = 'r446212.mdl.sandia.gov'
#     port = 8042
#     dbname = "lab"
#
#     client = InfluxDBClient(host, port, "root", "root", dbname, ssl=True, verify_ssl=False, cert=('R446656.crt', 'R446656.key'))
#     json_body = list()
#     json_body.append(
#         {
#             "measurement": "testmeas",
#             "tags": {
#                 "serial": 1,
#                 "instrument": "myinst",
#             },
#             "fields": {
#                 "temp": float(24),
#                 "hum": float(44),
#             }
#         })
#     client.write_points(json_body)
#     print("added {} points".format(len(json_body)))


def test_influx():
    host = "r446212.mdl.sandia.gov"
    port = 8086
    dbname = "lab"

    client = InfluxDBClient(host, port, "root", "root", dbname)
    json_body = list()
    json_body.append(
        {
            "measurement": "test44",
            "tags": {
                "serial": "1",
                "instrument": "myinst",
            },
            "fields": {
                "value": 12.34
            },
        })
    client.write_points(json_body)
    print("added {} points".format(len(json_body)))


if __name__ == "__main__":
    test_influx()