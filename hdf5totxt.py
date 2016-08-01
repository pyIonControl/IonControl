# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import argparse
import h5py
import numpy
from itertools import zip_longest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract data from hdf5 datasets.')
    parser.add_argument('filename', type=str, help='hdf5 filename')
    parser.add_argument('columns', metavar='column', type=str, nargs='+',
                       help='columns to be printed')

    args = parser.parse_args()

    columnnames = [n if n[0] == '/' else '/columns/{0}'.format(n) for n in args.columns]
    with h5py.File(args.filename) as f:
        columns = [numpy.array(f[column]) for column in columnnames]
        for l in zip_longest(*columns):
            print("\t".join(map(repr,l)))