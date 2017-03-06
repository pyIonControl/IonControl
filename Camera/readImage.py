#!/usr/bin/python
#-*- coding: latin-1 -*-
"""Load image files which have been saved by WinSIS."""

from __future__ import with_statement
import numpy
from numpy import fromfile, uint16, uint8, uint32, log, fromstring, ma
import os.path, sys, time



def read(filename):
    fid = open(filename, 'rb')
    foo = fid.read(10)
    #fid1 = open(filename, 'rb')
    height = int(fromfile(fid, dtype = uint16, count = 1))
    width  = int(fromfile(fid, dtype = uint16, count = 1))
    print("h=",height,"w=",width)
    fid.read(181)
    raw  = int(fromfile(fid, dtype = uint8 , count = 1))
    print(raw)
    xoff = int(fromfile(fid, dtype = uint16, count = 1))
    yoff = int(fromfile(fid, dtype = uint16, count = 1))


    #img = fromfile(fid, dtype = numpy.int32, count = width*height)
    data = read_fid_full(fid, size = width*height*2, timeout = 5)
    #print(data)
    img = fromstring(data, dtype = uint16, count = width*height)
    img.shape = (height, width)
    #print(img.shape)
    #print(img)

    #if (raw == 1):
    #    img = (img+1.0)*1000.0

    fid.close()
    #return img.astype(numpy.float_)
    return img.astype(numpy.float32)

def read_fid_full(fid, size, timeout = 1):
    numbytesread = 0
    result=bytes()
    starttime = time.clock()
    while numbytesread < size:
        #aa=fid.read(size - numbytesread)
        #print(aa)
        result += fid.read(size - numbytesread)
        #result=str.join(result,aa)
        numread = len(result)


        if time.clock() - starttime > timeout or numread>=size:
            break
        time.sleep(0.1)
    return result

def write_raw_image(filename, img, raw = False):
    fid = open(filename, 'wb')#file(filename, 'wb')
    fid.write(b' '*10)
    height, width = img.shape
    ha = numpy.array([height], dtype = numpy.uint16)
    ha.tofile(fid)
    wa = numpy.array([width], dtype = numpy.uint16)
    wa.tofile(fid)
    fid.write(b' '*181)
    if raw == True:
        fid.write('\x01')
    else:
        fid.write(b' ')
    fid.write(b' '*4) #TODO: Scan Parameters
    if img.dtype == numpy.uint16:
        img.tofile(fid)
    else:
        img.astype(uint16).tofile(fid)
    print(img)
    fid.close()

def loadimg(filename):
    img = read(filename)

    h, w = img.shape
    imgYb = img
    imgRb = img
    #imgYb = img[:h/2]
    #imgRb = img[h/2:]
    #return imgYb/1000.0 - 1, imgRb/1000.0 - 1
    return ma.masked_where(imgYb==0, imgYb/1000.0-1.0), \
           ma.masked_where(imgRb==0, imgRb/1000.0-1.0)

def loadimg3(path):
    img1 = read(os.path.join(path, 'PIC1.SIS'))
    img2 = read(os.path.join(path, 'PIC2.SIS'))
    img3 = read(os.path.join(path, 'PIC3.SIS'))

    img = - (log(img1 - img3) - log(img2 - img3))
    return img[:1040], img[1040:], 

def test_write_read():
    imgRb, imgYb = loadimg('img/rawimg1.sis')
    #imgRb, imgYb = loadimg3('this string is for nothing')

    rawimg = (1000*(imgRb + 1)).astype(numpy.uint16)
    
    write_raw_image('img/testsave.sis', rawimg)
    rawimgsaved = read('img/testsave.sis')

def test_read(filename):
    print("loading...")
    sys.stdout.flush()
    loadimg(filename)
    print("done")
    sys.stdout.flush()

def test_save(filename, img):
    print("saving...")
    sys.stdout.flush()
    write_raw_image(filename, img)
    print("done")
    sys.stdout.flush()

def simultanous_write_read():
    import threading
    imgRb, imgYb = loadimg('img/rawimg1.sis')
    rawimg = (1000*(imgRb + 1)).astype(numpy.uint16)

    savethread = threading.Thread(target = test_save,
                                  args = ('img/testsave.sis', rawimg),
                                  )

    loadthread = threading.Thread(target = test_read,
                                  args = ('img/testsave.sis',),
                                  )

    savethread.run()
    loadthread.run()
    
    


if __name__ == '__main__':
    #img=read("Z:/Lab/Andor Project/imaging_software_g/bitmaps/80up_1.fits")
    #aa = numpy.array(range(5 * 5))
    #aa.reshape(5, 5)
    #filename='C:/IonControl/Camera/Images/YourMom.sis'
    #write_raw_image(filename, aa , raw=False)
    filename = 'C:/IonControl/Camera/Images/20170305194438-ScanName-Image-number.sis'
    img = read(filename)
    test_save("C:/IonControl/Camera/Images/cane",img)
    #simultanous_write_read()
    
