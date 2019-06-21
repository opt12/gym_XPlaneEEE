# -*- coding: utf-8 -*-
import sys
import socket
import os
import os.path
import json
import time
from threading import Thread
import threading 
import ctypes 
from gym_XPlaneEEE.utils.dataCenter import DataCenter
from gym_XPlaneEEE.utils.singleton import SingletonMixin


#TODO remove all references to printFlag
from gym_XPlaneEEE.utils.xPlaneGymCalculations import prepareInitialPlaneState
printFlag = 0

class IpcClient(Thread, SingletonMixin):
    def __init__ (self):
        Thread.__init__(self)
        self.continueFlag = True
        self.dc = DataCenter.instance()
        self.client = None
        self.socketName = None
    
    def connect(self, socketName):
        #close an existing connection
        if self.client:
            try:
                self.client.close
            except Exception as inst:
                print(type(inst))    # the exception instance
                print(inst.args)     # arguments stored in .args
                print(inst)          # __str__ allows args to be printed directly, but may be overridden in exception subclasses
            self.client = None
        self.socketName = socketName
        print ("Connecting...")
        if os.path.exists(self.socketName):
            self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                self.client.connect(self.socketName)
            except:
                print("couldn't connect to ", self.socketName ,". Quitting!")
                raise ConnectionError("couldn't connect to ", self.socketName ,". Quitting!")
                # time.sleep(1)   #specify the time between retries here
                # continue
        else:
            raise ConnectionError (self.socketName ," does not exist. Quitting!")
            # time.sleep(1)
            # continue

    def getSocketName(self):
        return self.socketName
    
    def run(self):
        if not self.socketName:
            raise ConnectionError("No socketName set to connect to. Use setSocketName(sn) before starting listener thread.")
        global printFlag
        print ("Ready.")
        print ("Ctrl-C to quit.")
        while True:
            if not self.continueFlag:
                break
            datagram = self.client.recv( 2048 )
            if not datagram:
                break
            else:
                # print ("-" * 20)
                # print (datagram)
                try:
                    socketData = json.loads(datagram[:-1])  #there is an extra `\f` character at the end of the data; see SockServer.cpp
                    if(socketData['type'] == 'PLANE_STATE'):
                        if printFlag>0:
                            print (json.dumps(socketData, sort_keys=True, indent=4))
                            printFlag -= 1
                        # print("PLANE_STATE received")
                        self.dc.putState(socketData['data'])
                    else:
                        print (json.dumps(socketData, sort_keys=True, indent=4))
                except ValueError as inst:
                    print(type(inst))    # the exception instance
                    print(inst.args)     # arguments stored in .args
                    print(inst)          # __str__ allows args to be printed directly, but may be overridden in exception subclasses
                except Exception as inst:
                    print(type(inst))    # the exception instance
                    print(inst.args)     # arguments stored in .args
                    print(inst)          # __str__ allows args to be printed directly, but may be overridden in exception subclasses
        print ("Lost Connection!")
        try:
            self.client.close
        except Exception as inst:
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)          # __str__ allows args to be printed directly, but may be overridden in exception subclasses
        self.client = None
        print ("Done. Quitting IPC-Client Thread now.")
    
    def setContinueFlag(self, flag):
        self.continueFlag = True if flag == True else False
        print("continueFlag = %r" % self.continueFlag)
    
    def socketSendData(self, msgTypeStr, requestId, dataDict):
        if self.client == None:
            print("No connection available. Try again later.")
            return False
        else:
            j = {}
            j['type']      = msgTypeStr
            j['requestId'] = requestId
            j['data']      = dataDict
            try:
                # see https://stackoverflow.com/a/42612820/2682209
                # print(json.dumps(j, indent=4, sort_keys=True))
                self.client.send(json.dumps(j).encode('utf-8'))
            except Exception as inst:
                print(type(inst))    # the exception instance
                print(inst.args)     # arguments stored in .args
                print(inst)          # __str__ allows args to be printed directly, but may be overridden in exception subclasses
                #TODO raise inst
                return False
        return True


if __name__ == '__main__':
    #start a listener thread
    ipcClient = IpcClient.instance()
    ipcClient.setSocketName("/tmp/eee_AutoViewer")
    ipcClient.start()

    # youself go watch wheter the program is supposed to stop and gracefully stop the threads
    keyPress = ''
    print("Press Ctrl-C to quit")
    while True:
        # keyPress = input()
        # if(keyPress == 'q' or keyPress == 'Q'):
        #     break
        time.sleep(15)
        print("sending message to socket")
        message = prepareInitialPlaneState()
        ipcClient.socketSendData(b"SET_PLANE_STATE", 1, message['data'])
        printFlag = 3
    ipcClient.setContinueFlag(False)


    print ("Stopping Main Thread")
