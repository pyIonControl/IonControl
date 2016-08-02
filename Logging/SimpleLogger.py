# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import datetime
import time
from externalParameter.MKSReader import MKSReader
from externalParameter.TerranovaReader import TerranovaReader
import os
from modules.RunningStat import RunningStatHistogram

MaxRecordingInterval = 180
QueryInterval = 0

if __name__=="__main__":
    terra = TerranovaReader(port=3, timeout=0.5) #
    terra.open()
    mks = MKSReader(timeout=0.5)
    mks.open()
    HistogramStat = RunningStatHistogram()
    TerraStat = RunningStatHistogram()
    LastRecordingTime = 0
    with open("pressurelog-triangle.txt", 'a') as f:
        while (True):
            try:
                value = mks.value()
                HistogramStat.add( value )
                value_terra = terra.value()
                TerraStat.add( value_terra )
                if time.time()-LastRecordingTime > MaxRecordingInterval or len(HistogramStat.histogram)>2 or len(TerraStat.histogram)>2:
                    LastRecordingTime = time.time()
                    message = "{0} {1} {2} {3} {4} {5} {6} {7} {8}".format(datetime.datetime.now(), HistogramStat.mean, HistogramStat.count, HistogramStat.min, HistogramStat.max,
                                                                       TerraStat.mean, TerraStat.count, TerraStat.min, TerraStat.max )
                    f.write(message + "\n")
                    print(message)
                    f.flush()
                    os.fsync(f)
                    HistogramStat.clear()
                    TerraStat.clear()
                time.sleep(QueryInterval)
            except Exception as e:
                print(e)
                mks.close()
                mks.open()
            
            