# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import subprocess
import os.path

def convertSvgEmf(inkscapeExecutable, filename):
    basename, ext = os.path.splitext(filename)
    emfname = basename + ".emf"
    subprocess.call([inkscapeExecutable, filename, "--export-emf={0}".format(emfname)])

def convertSvgPdf(inkscapeExecutable, filename):
    basename, ext = os.path.splitext(filename)
    pdfname = basename + ".pdf"
    subprocess.call([inkscapeExecutable, filename, "--export-pdf={0}".format(pdfname)])