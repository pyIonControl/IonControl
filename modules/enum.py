# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from collections import OrderedDict


def enum(*sequential, **named):
    enums = OrderedDict(list(zip(sequential, list(range(len(sequential))))), **named)
    reverse, forward = dict((value, key) for key, value in enums.items()), enums.copy()
    enums['reverse_mapping'] = reverse
    enums['mapping'] = forward
    return type('Enum', (), enums)
    
if __name__ == "__main__":
    Numbers = enum('ZERO', 'ONE', 'TWO')
    state = Numbers.ZERO
    print(state)
    print(state == 0)
    state = 1
    print(state == Numbers.ONE)
    print(Numbers.mapping['ZERO'])
    print(Numbers.reverse_mapping[2])
    print(list(Numbers.mapping.keys()))
    print(Numbers.mapping)
