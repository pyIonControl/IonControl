import pytest
from influxdb import InfluxDBClient


def test_influx_ssl():
    host = 'localhost'
    port = 8042
    dbname = "lab"

    client = InfluxDBClient(host, port, "root", "root", dbname, ssl=True, verify_ssl=False)
    json_body = list()
    json_body.append(
        {
            "measurement": "testmeas",
            "tags": {
                "serial": 1,
                "instrument": "myinst",
            },
            "fields": {
                "temp": float(24),
                "hum": float(44),
            }
        })
    client.write_points(json_body)
    print("added {} points".format(len(json_body)))


def test_influx_ssl_verify():
    host = "r446212.mdl.sandia.gov"
    port = 8042
    dbname = "lab"

    client = InfluxDBClient(host, port, "root", "root", dbname, ssl=True, verify_ssl=True)
    json_body = list()
    json_body.append(
        {
            "measurement": "testmeas",
            "tags": {
                "serial": 1,
                "instrument": "myinst",
            },
            "fields": {
                "temp": float(24),
                "hum": float(44),
            }
        })
    client.write_points(json_body)
    print("added {} points".format(len(json_body)))


