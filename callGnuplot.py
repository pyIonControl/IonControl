# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import subprocess

proc = subprocess.Popen(["C:\Program Files (x86)\gnuplot\\bin\pgnuplot.exe",'-persist'],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                        )

proc.stdin.write(b"plot sin(x)\n")
proc.stdin.flush()
