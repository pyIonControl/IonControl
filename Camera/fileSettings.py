import os, os.path
import time

#basedir = r"c:/fit/siscam"
basedir = os.getcwd()
#print("This is the basedir = ", basedir)
#full path to image file
#imagefile = r"c:/fit/ocf/fit2.sis"
imagefile = os.path.join(basedir, 'Camera/Images/test.sis')
rawimage1file = os.path.join(basedir, 'Images/rawimg1.sis')
rawimage2file = os.path.join(basedir, 'img/rawimg2.sis')
rawimage3file = os.path.join(basedir, 'img/rawimg3.sis')

#file for automatic parameter retrieval
paramfile = os.path.join(basedir, 'img/parameters.dat')
paramfile2 = os.path.join(basedir, 'img/parameters2.dat')

#file for feedback to experiment control
feedbackfile = os.path.join(basedir, 'img/feedback.dat')

#where to save images
#imagesavepath = r"F:/ytterbium/data/CamData"
imagesavepath = os.path.join(basedir, 'Camera/Images') #10/04/14 changed / separator with \\
#imagesavepath = r"y:/data/2008/" #direct access to cam computer

#icons, etc.
bitmappath = os.path.join(basedir, 'bitmaps')

#directory to store template files
templatedir = os.path.join(basedir, 'templates')

##acquire

useAndor = True

