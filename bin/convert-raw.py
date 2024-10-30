#!/usr/bin/env python

import os, sys, time
import numpy as np
import pyrogue as pr
import ePixViewer.Cameras as cameras
import ePixViewer.imgProcessing as imgPr

import h5py

NUMBER_OF_PACKETS_PER_FRAME = 2
MAX_NUMBER_OF_FRAMES_PER_BATCH  = -1

PAYLOAD_SERIAL_FRAME = 4112 #2064
PAYLOAD_TS           = 7360

##################################################
# Global variables
##################################################
cameraType            = 'cryo64xN'
bitMask               = 0xffff
SAVE_HDF5             = True

##################################################
# Dark images
##################################################
#
filename = sys.argv[1]

f = open(filename, mode = 'rb')

file_header = [0]
numberOfFrames = [0 , 0]
previousSize = 0
asicID = 0
while ((len(file_header)>0) and ((numberOfFrames[0]<MAX_NUMBER_OF_FRAMES_PER_BATCH) or (numberOfFrames[1]<MAX_NUMBER_OF_FRAMES_PER_BATCH) or (MAX_NUMBER_OF_FRAMES_PER_BATCH==-1))):
    try:
        # reads file header [the number of bytes to read, EVIO]
        file_header = np.fromfile(f, dtype='uint32', count=2)
        print("header 0: ", file_header[0])
        print("header 1: ", (file_header[1]&0xff000000)>>24)
        payloadSize = int(file_header[0]/4)-1 #-1 is need because size info includes the second word from the header

        newPayload = np.fromfile(f, dtype='uint32', count=payloadSize) #(frame size splited by four to read 32 bit 
        print ("Payload" , numberOfFrames, ":",  (newPayload[0:5]))
        #save only serial data frames
        if ((file_header[1]&0xff000000)>>24)==1: #image packet only, 2 mean scope data
            asicID = (newPayload[0]&0x00000010)>>4
            if asicID == 0:
                if (numberOfFrames[asicID] == 0):
                    allFrames_0 = [newPayload.copy()]
                else:
                    newFrame  = [newPayload.copy()]
                    allFrames_0 = np.append(allFrames_0, newFrame, axis = 0)
                numberOfFrames[asicID] = numberOfFrames[asicID] + 1 
                print ("Payload 0" , numberOfFrames, ":",  (newPayload[0:5]))
                previousSize = file_header
            if asicID == 1:
                if (numberOfFrames[asicID] == 0):
                    allFrames_1 = [newPayload.copy()]
                else:
                    newFrame  = [newPayload.copy()]
                    allFrames_1 = np.append(allFrames_1, newFrame, axis = 0)
                numberOfFrames[asicID] = numberOfFrames[asicID] + 1 
                print ("Payload 1 " , numberOfFrames, ":",  (newPayload[0:5]))
                previousSize = file_header

        if (numberOfFrames[asicID]%1000==0):
            print("Read %d frames" % numberOfFrames)

    except Exception: 
        e = sys.exc_info()[0]
        #print ("Message\n", e)
        print ('size', file_header, 'previous size', previousSize)
        print("numberOfFrames read: " ,numberOfFrames)

#%%
##################################################
# image descrambling
##################################################
currentCam = cameras.Camera(cameraType = cameraType)
currentCam.bitMask = bitMask
#numberOfFrames = allFrames.shape[0]
print("numberOfFrames in the 3D array: " ,numberOfFrames)
print("Starting descrambling images")
currentRawData = []
asicID = 0
imgDesc_0 = []
if(numberOfFrames[asicID]==1):
    [frameComplete, readyForDisplay, rawImgFrame] = currentCam.buildImageFrame(currentRawData = [], newRawData = allFrames_0[0])
    imgDesc_0 = np.array([currentCam.descrambleImage(bytearray(rawImgFrame.tobytes()))])
else:
    for i in range(0, numberOfFrames[asicID]):
        #get an specific frame
        [frameComplete, readyForDisplay, rawImgFrame] = currentCam.buildImageFrame(currentRawData, newRawData = allFrames_0[i,:])
        currentRawData = rawImgFrame

        #get descrambled image from camera
        if (len(imgDesc_0)==0 and (readyForDisplay)):
            imgDesc_0 = np.array([currentCam.descrambleImage(rawImgFrame)],dtype=float)
            currentRawData = []
        else:
            if readyForDisplay:
                currentRawData = []
                newImage = currentCam.descrambleImage(rawImgFrame)
                newImage = newImage.astype(float, copy=False)
                #if (np.sum(np.sum(newImage))==0):
                #    newImage[np.where(newImage==0)]=np.nan
                imgDesc_0 = np.concatenate((imgDesc_0, np.array([newImage])),0)
#############################
currentRawData = []
asicID = 1
imgDesc_1 = []
if(numberOfFrames[asicID]==1):
    [frameComplete, readyForDisplay, rawImgFrame] = currentCam.buildImageFrame(currentRawData = [], newRawData = allFrames_1[0])
    imgDesc_1 = np.array([currentCam.descrambleImage(bytearray(rawImgFrame.tobytes()))])
else:
    for i in range(0, numberOfFrames[asicID]):
        #get an specific frame
        [frameComplete, readyForDisplay, rawImgFrame] = currentCam.buildImageFrame(currentRawData, newRawData = allFrames_1[i,:])
        currentRawData = rawImgFrame

        #get descrambled image from camera
        if (len(imgDesc_1)==0 and (readyForDisplay)):
            imgDesc_1 = np.array([currentCam.descrambleImage(rawImgFrame)],dtype=float)
            currentRawData = []
        else:
            if readyForDisplay:
                currentRawData = []
                newImage = currentCam.descrambleImage(rawImgFrame)
                newImage = newImage.astype(float, copy=False)
                #if (np.sum(np.sum(newImage))==0):
                #    newImage[np.where(newImage==0)]=np.nan
                imgDesc_1 = np.concatenate((imgDesc_1, np.array([newImage])),0)
if(SAVE_HDF5):
    print("Saving Hdf5")
    h5_filename = os.path.splitext(filename)[0]+".hdf5"
    #h5_filename = os.path.splitext(os.path.basename(filename))[0] + '.hdf5'
    f = h5py.File(h5_filename, "w")
    f.create_dataset('adcData_0', data=imgDesc_0.astype('uint16'), compression='gzip')
    f.create_dataset('adcData_1', data=imgDesc_1.astype('uint16'), compression='gzip')
    #f['adcData_0'] = imgDesc_0.astype('uint16')
    #f['adcData_1'] = imgDesc_1.astype('uint16')
