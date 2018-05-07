from websocket import create_connection
import json
from influxdb import InfluxDBClient

while True:
    ws = create_connection("ws://192.168.1.222:8088/index.htm")
    client = InfluxDBClient('r446212.mdl.sandia.gov', 8086, 'root', 'root', 'lab')

    try:
        while True:
            msg = json.loads(ws.recv())
            if msg['message_type'] == "left_panel":
                msg.pop('message_type')
                msg.pop('browser_tab')
                tags = {key: value for key, value in msg.items() if type(value) == str}
                fields = {key: value for key, value in msg.items() if type(value) == float}
                json_body = [
                     {
                         "measurement": "solstice_2220",
                         "tags": tags,
                         "fields": fields,
                    }
                ]
                client.write_points(json_body)
                #print(msg['lp_power'])
    except Exception as e:
        print("Exception: {}, retrying.".format(e))
