import pickle

class A:
    def __init__(self, value):
        print("__init__", value)
        self.value = value

    def __getnewargs__(self):
        print("__getnewargs__")
        return (self.value, )

    def __getstate__(self):
        print("__getstate__")
        return None

    def __setstate__(self, state):
        print("__setstate__")

    def __repr__(self):
        return str(self.__dict__)

    def __reduce__(self):
        print("__reduce__")
        return A, (self.value, )

a = A("Peter")
a.hidden = 137

s = pickle.dumps(a)
b = pickle.loads(s)

print(b)