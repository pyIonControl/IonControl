import serial.tools.list_ports

known_serial = {'FTF931DZA': 'SRS RGA',
                'FTK5D5LTA': 'Oven controller',
                'FTHBHTL5A': 'USB serial MKS gauge',
                'FTHBHXLZA': 'USB serial Ion Gauge'}


if __name__ == "__main__":
    for desc in serial.tools.list_ports.comports():
        print("Device: {device}, Product: {product}, Serial: {serial_number}, Manufacturer: {manufacturer}, Description: {description}".format(**vars(desc)),
              "Comment: {}".format(known_serial.get(desc.serial_number)))