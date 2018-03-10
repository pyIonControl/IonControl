import argparse

from influxdb import InfluxDBClient
from dateutil import parser

def parse_args():
    """Parse the args."""
    parser = argparse.ArgumentParser(
        description='Insert Madgetech temperature and humidity data into influx (export as excel and save from excel as csv)')
    parser.add_argument('--host', type=str, default='r446212.mdl.sandia.gov', help='hostname of InfluxDB http API')
    parser.add_argument('--instrument', type=str, required=True, help='name of instrument to be recorded')
    parser.add_argument('--measurement', type=str, default="room_temperature", help='name of influxdb series')
    parser.add_argument('--dbname', type=str, default="lab", help='name of influxdb database')
    parser.add_argument('filename', type=str, help='filename of .csv data file')
    parser.add_argument('--timezone', type=str, default='-0700', help='timezone of csv data -0700 for MST')
    return parser.parse_args()


def read_and_record(measurement="room_temperature", instrument="front", host="r446212.mdl.sandia.gov",
                    dbname="lab", filename=None, timezone="-0700"):
    port = 8086

    client = InfluxDBClient(host, port, "root", "root", dbname)
    data = list()
    with open(filename, 'r') as f:
        for i in range(2):
            next(f)
        _, _, serial, _ = next(f).split(",")
        for i in range(4):
            next(f)
        for line in f:
            data.append(line.split(","))

    query = "select * from {} where instrument='{}' order by time desc limit 1".format(measurement, instrument)
    results = client.query(query)
    if results:
        last_recorded_time = parser.parse(list(results)[0][0]['time'])
    else:
        last_recorded_time = parser.parse("1/1/1970 00:00:00+0000")

    json_body = list()
    for item in data:
        date, time, temp, hum = item
        dt = parser.parse(" ".join((date, time, timezone)))
        if dt > last_recorded_time:
            json_body.append(
                {
                    "measurement": measurement,
                    "tags": {
                        "serial": serial,
                        "instrument": instrument,
                    },
                    "time": int(dt.timestamp())*1000000000,
                    "fields": {
                        "temp": float(temp),
                        "hum": float(hum),
                    }
                })
    client.write_points(json_body)
    print("added {} points".format(len(json_body)))


if __name__ == "__main__":
    args = parse_args()
    read_and_record(**vars(args))


