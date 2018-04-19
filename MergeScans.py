from pathlib import Path
from trace.TraceCollection import TraceCollection
import numpy as np
import argparse

parser = argparse.ArgumentParser(description='Merge multiple scans into single file')

parser.add_argument('filename', type=str, default=None, nargs='+', help='filename of trace scan')
parser.add_argument('--path', action="store", type=str, help="path to files")
parser.add_argument('--new-filename', action="store", type=str, help="name of new file")

args = parser.parse_args()
commonPath = Path(args.path)

filename = args.filename[0]
filename = str(commonPath / filename)

# Trace = TraceCollection()
# Trace.loadTracePlain(filename)
# scanData = Trace
# for otherfilename in args.filename[1:]:
#     otherTrace = TraceCollection()
#     otherTrace.loadTracePlain(str(commonPath / otherfilename))
#     file1 = otherTrace
#     for key, value in otherTrace.items():
#         scanData[key].extend(value)

#scanData.saveHdf5()

#newfile = commonPath / args.new_filename
#scanData.saveHdf5(newfile)


newtext = Path(filename).read_text()
import csv
for fname in args.filename[1:]:
    fname = commonPath / fname
    with open(str(fname), 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter='\t')
        for row in reader:
            if '#' not in row[0]:
                strrow = ''
                for col, items in enumerate(row):
                    strrow += items + '\t'
                newtext += str(strrow) +'\n'

newpath = commonPath / args.new_filename
Path(newpath).write_text(newtext)


