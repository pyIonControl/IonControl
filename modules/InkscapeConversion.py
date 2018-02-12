# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import fileinput
import subprocess
import os.path
from pathlib import Path
from pdfrw import PdfReader, PdfWriter

def convertSvgEmf(inkscapeExecutable, filename):
    basename, ext = os.path.splitext(filename)
    emfname = basename + ".emf"
    subprocess.call([inkscapeExecutable, filename, "--export-emf={0}".format(emfname)])

def convertSvgWmf(inkscapeExecutable, filename):
    basename, ext = os.path.splitext(filename)
    emfname = basename + ".wmf"
    subprocess.call([inkscapeExecutable, filename, "--export-wmf={0}".format(emfname)])

def convertSvgPdf(inkscapeExecutable, filename, depfiles=None):
    basename, ext = os.path.splitext(filename)
    pdfname = basename + ".pdf"
    subprocess.check_call([inkscapeExecutable, filename, "--export-pdf={0}".format(pdfname)])
    if depfiles is not None:
        addPdfMetaData(pdfname, basename+"tmp.pdf", depfiles)

def addPdfMetaData(pdfname, outname, filenames):
    localname = str(Path(pdfname))
    pdf = PdfReader(localname)
    pdf.Info.Keywords = '\n'.join(filenames)
    PdfWriter().write(str(outname), pdf)
    Path(outname).replace(pdfname)

def getPdfMetaData(pdfname):
    pdf = PdfReader(pdfname)
    kw = pdf.Info.Keywords
    if kw is not None:
        kwlist = kw[1:-1].splitlines()
        return kwlist
    else:
        return []

def addSvgMetaData(svgname, filenames):
    ln = 0
    if filenames:
        for line in fileinput.input(svgname, inplace=True):
            print(line)
            if ln == 0:
                print("<!-- Files")
                for fn in filenames:
                    print(fn)
                print("-->")
            ln += 1

def getSvgMetaData(svgname):
    with open(svgname) as f:
        filelist = set()
        startRecording = False
        for line in f:
            if line == "-->\n":
                return filelist
            if startRecording:
                filelist.add(line.rstrip())
            if line == "<!-- Files\n":
                startRecording = True

