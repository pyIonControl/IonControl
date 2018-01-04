# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import cProfile
import pstats

import wrapt


def doprofile(func):
    def profiled_func(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            sortby = 'tottime'
            ps = pstats.Stats(profile).sort_stats(sortby)            
            ps.print_stats()
            ps.dump_stats("profile.pkl")
            ps.dump_stats(func.__name__ + ".pkl")
    return profiled_func


def profileaccum(profile):
    @wrapt.decorator
    def profiled_func(wrapped, instance, args, kwargs):
        profile.enable()
        result = wrapped(*args, **kwargs)
        profile.disable()
        return result
    return profiled_func


def saveProfile(profile, filename="profile.pkl", sortby="tottime"):
    ps = pstats.Stats(profile).sort_stats(sortby)
    ps.print_stats()
    ps.dump_stats(filename)

