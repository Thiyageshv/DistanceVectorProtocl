#!/usr/bin/env python

import socket,pickle 
import json 
import errno
from socket import error as socket_error 

import sys
import collections
import time
import Queue
import threading
import time

from threading import Thread
from SocketServer import ThreadingMixIn



def changed(a,b):
   
    if set(a) & set(b):
        return 0
    return 1
    
def checktimeout(starttime):
    global timeout
    curtime = time.time()
    if (int(curtime - starttime))%timeout == 0:
        return 1
    return 0 
    
def showrt():
    global viavec
    global disvec
    
    for i in disvec:
        t = i.split(":")
        t1 = t[0].split(" ")
        t0 = t[1].split("|")
        if int(t0[0]) < 256:
            if t1[1] in viavec[t1[1]] == t1[1]:
                print t1[1], "is directly available at cost ", t0[0]
            else:
                print t1[1], "is available at cost ", t0[0], " via ", viavec[t1[1]] 
        else:
            print t1[1], " is either unreachable at the moment or is lost forever :( " 

    
    
       
    
class sendthread(Thread):
    def __init__(self):
        Thread.__init__(self)
        print "send thread started"
    def run(self):
        global disvec
        
        global dvlist
        global dv
        global neighbor
        global nodedetails 
        global vectorack
        global vectordata 
        global listnodes
        global vectorchange 
        global disvecbefore 
        global viavec
        global closedflag
        disvecbefore = []
        
       
        print "Send distance vector updates"
       
        sock1 = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
       
        checksum = 0
        while checksum < len(neighbor):
           
            for i in neighbor:
                temp = [] 
                temp.append(str(listeningport) + " " + i + ":" + str(nodedetails[i].weight) + "|")
                datastring = "".join(temp) 
                checksum = checksum + vectorack[i]
                #print checksum
            
                if vectorack[i] == 0:                    
                    try:
                        
                        sock1.sendto(datastring, (nodedetails[i].ip , int(nodedetails[i].port)))
                   
                    except socket_error as serr:
                        if serr.errno == errno.ECONNREFUSED:
                            break
        
            time.sleep(2.0)
          
      
        vectorchange = 1
        starttime = time.time()
        
        while closedflag != 1:
            flag = 0
            
        
            #print "disvec before" , disvec    
            ind = -1 
            for i in disvec:
                t = i.split(":")
                t1 = t[0].split(" ")
                t0 = t[1].split("|")
                mini = int(t0[0])
                ind = ind + 1
                for j in neighbor:
                    
                    if t1[1] == j:
                        continue 
                        
                    try:
                        if dv[j][t1[1]] is not None:
                         
                            if mini > int(nodedetails[j].weight) + int(dv[j][t1[1]]):
                                mini = int(nodedetails[j].weight) + int(dv[j][t1[1]])
                                lock.acquire()
                                disvec[ind] = t[0] + ":" + str(mini) + "|"
                                viavec[t1[1]] = j
                                lock.release()
                                vectorchange = 1
                        
                    except KeyError:   
                                  
                        continue
                
            datastring = "".join(disvec)
            #print "Sending", disvec 
            for z in neighbor:
                if z in nodedetails and nodedetails[z].status != 0 :
                    sock1.sendto(datastring, (nodedetails[z].ip , int(nodedetails[z].port)))
                
            disvecbefore = list(disvec)  
            time.sleep(float(timeout)) 
                
        
      
        
class readthread(Thread):
    def __init__(self):
        Thread.__init__(self)
       
        print "read thread started"
    def run(self):
        global listeningport 
        global vectorack
        global vectordata
        global neighbor 
        global listnodes
        global disvec
        global disvecbefore 
        global viavec
        global closedflag
       
        mini = 256
        print "keep listening for incoming distance vectors"
        sock2 = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
     
        sock2.bind(("127.0.0.1", int(listeningport)))
        checksumack = 0
        checksumdata = 0
        while closedflag != 1:
            #print "disvec", disvec 
            try:
                update, addr = sock2.recvfrom(2048)
                #print update 
            except socket.timeout:
                print "timeout"
                break
            if "ACK" in update:
                ackcontent = update.split("-")
                sendid = addr[0] + "-" + ackcontent[0]
                if vectorack[sendid] == 0:
                    vectorack[sendid] = 1
                    checksumack = checksumack + vectorack[sendid]
            
            elif "LINKDOWN" in update or "LINKDOWNSELF" in update:
                
                if "LINKDOWNSELF" in update:
                    thiscon = update.split(" ")
                    senderid = thiscon[1]
                else:
                    flag = 0
                    updatecontent = update.split(" ")
                    senderid = addr[0] + "-" + updatecontent[0]
                
                nodedetails[senderid].weight = 256
                nodedetails[senderid].status = 0
                #check viavec, if this node present in path update disvec
                nodedetails[senderid].lastupdate = time.time()
                #print "change disvec because of linkdown message"
                oldnodeidindex = -1
                for i in disvec:    
                    t = i.split(":")
                    t0 = t[1].split("|")
                    t1 = t[0].split(" ")
                    oldnodeidindex = oldnodeidindex + 1
                    if t1[1] == senderid or ( t1[1] in viavec.keys() and viavec[t1[1]] == senderid):
                        if t1[1] in viavec.keys() and viavec[t1[1]] == senderid and t1[1] != senderid:
                            if t1[1] in neighbor and nodedetails[t1[1]].status == 1: 
                                if t0[0] != 256:
                                    lock.acquire()
                                    newdisvec = str(listeningport) + " " + t1[1] + ":" +  str(nodedetails[t1[1]].weight) + "|"
                                    disvec[oldnodeidindex] = newdisvec
                                    lock.release()
                                    viavec[t1[1]] = t1[1]
                                elif t0[0] == 256:
                                    lock.acquire()
                                    newdisvec = str(listeningport) + " " + t1[1] + ":" +  str(256) + "|"
                                    disvec[oldnodeidindex] = newdisvec
                                    lock.release()
                                    del viavec[t1[1]]
                                    
                            else:
                                lock.acquire()
                                newdisvec = str(listeningport) + " " + t1[1] + ":" +  str(256) + "|"
                                disvec[oldnodeidindex] = newdisvec    
                                lock.release()
                                del viavec[t1[1]]
                                
                      
                        else:
                         
                            lock.acquire()
                            newdisvec = str(listeningport) + " " + senderid + ":" +  str(256) + "|"
                            disvec[oldnodeidindex] = newdisvec
                            try:
                                del viavec[t1[1]]
                            except KeyError:
                                pass
                            lock.release()
                                
                datastringurgent = "".join(disvec)
                #print "sending triggered update", disvec
                for z in neighbor:
                    if nodedetails[z].status != 0:
                        sock2.sendto(datastringurgent, (nodedetails[z].ip , int(nodedetails[z].port)))
                                   
            
            elif "LINKUP" in update: 
                updatecontent = update.split(" ")
                senderid = addr[0] + "-" + updatecontent[0]
                nodedetails[senderid].weight = nodedetails[senderid].previousweight 
                nodedetails[senderid].status = 1
                nodedetails[senderid].lastupdate = time.time()
                for i,j in enumerate(disvec):
                    if senderid in j:
                        lock.acquire()
                        disvec[i] = str(listeningport) + " " + senderid + ":" + nodedetails[senderid].weight + "|"
                        lock.release()
                        break
                        
                            
            else:
               
                #print "data received", update 
                data = update.split("|")
                content = data[0].split(" ")
                senderlisteningport = content[0]
                senderid = addr[0] + "-" + senderlisteningport
                nodedetails[senderid].lastupdate = time.time()
                dvlist = {}     
                for j in range(0,len(data)-1):
                    content = data[j].split(" ")
                    dvcontent = content[1].split(":")
                    dvlist[dvcontent[0]] = dvcontent[1]
                    dvconcon = dvcontent[0].split("-")
                    if dvcontent[0] not in listnodes and dvconcon[1] != str(listeningport):
                        listnodes.append(dvcontent[0])
                        strs = str(listeningport) + " " + dvcontent[0] + ":" + str(mini) + "|"
                        disvec.append(strs)
                    dv[senderid] = dvlist  
                    
                    if dvcontent[0] in viavec.keys() and viavec[dvcontent[0]] == senderid:
                        
                        for i,j in enumerate(disvec):
                            if dvcontent[0] in j:
                                newweight = int(dvcontent[1]) + int(nodedetails[senderid].weight)
                                if dvcontent[0] in neighbor and int(nodedetails[dvcontent[0]].weight) < newweight: 
                                    newweight = int(nodedetails[dvcontent[0]].weight)
                                    viavec[dvcontent[0]] = dvcontent[0]
                                 
                                lock.acquire()
                                disvec[i] = str(listeningport) + " " + dvcontent[0] + ":" + str(newweight) + "|"
                                lock.release()
                             
              
                ackstring = str(listeningport) + "-" + "ACK" 
                sock2.sendto(ackstring, (addr[0], int(senderlisteningport))) 
                
                
        if closedflag == 1:        
            sock2.close()
            sys.exit()
        
            
    
    
class menuthread(Thread):
    def __init__(self):
        Thread.__init__(self)
      
        print "menu thread started"
    def run(self):
        global listeningport 
        global vectorack
        global vectordata
        global neighbor 
        global listnodes
        global disvec
        global disvecbefore 
        global nodedetails
        global closedflag 
    
        sock3 = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        
        
        
        if 0 not in vectorack:
            while closedflag != 1: 
                flag = 0
                print "stablizing.........................."
                print "1. SHOW RT"
                print "2. LINK UP"
                print "3. LINK DOWN"
                print "4. CLOSE"
                ch = raw_input("Type your command")
                if ch == "SHOWRT": 
                    showrt()
                if "LINKDOWN" in ch:
               
                    try:
                        iden = ch.split(" ")
                        port = iden[1].split(":")
                        nodeid = port[0] + "-" + port[1] 
                        nodedetails[nodeid].weight = 256
                        nodedetails[nodeid].status = 0 #link down
                    except KeyError:
                        print "Who the hell is that? He is not my neighbor"
                    if nodeid in neighbor:
                        datastring = str(listeningport) + " " + "LINKDOWN"
                        sock3.sendto(datastring, (nodedetails[nodeid].ip , int(nodedetails[nodeid].port)))
                        oldnodeidindex = -1
                        for i in disvec:
                            oldnodeidindex = oldnodeidindex + 1
                            if flag == 1:
                                break
                            t = i.split(":")
                            t1 = t[0].split(" ")
                            if t1[1] == nodeid or viavec[t1[1]] == nodeid:
                                if viavec[t1[1]] == nodeid:
                                    if t1[1] in neighbor and nodedetails[t1[1]].status != 0:
                                        lock.acquire()
                                        newdisvec = str(listeningport) + " " + t1[1] + ":" +  str(nodedetails[t1[1]].weight) + "|"
                                        disvec[oldnodeidindex] = newdisvec
                                        viavec[t1[1]] = t1[1]
                                        lock.release()
                                
                                    else:
                                        lock.acquire()
                                        newdisvec = str(listeningport) + " " + t1[1] + ":" +  str(256) + "|"
                                        disvec[oldnodeidindex] = newdisvec
                                        del viavec[t1[1]]
                                        lock.release()
                                        
                                else:        
                                    lock.acquire()
                                    newdisvec = str(listeningport) + " " + nodeid + ":" +  str(256) + "|"
                                    disvec[oldnodeidindex] = newdisvec
                                    del viavec[t1[1]]
                        
                                    lock.release()
                                    
                      
                            
                    else:
                        print "Who the hell is that? He is not my neighbor"
                        
                    datastringurgent = "".join(disvec)
                    for z in neighbor:
                        if nodedetails[z].status != 0:
                            sock3.sendto(datastringurgent, (nodedetails[z].ip , int(nodedetails[z].port)))
                              
                if "LINKUP" in ch: 
                    #catch keyerror exception 
                    iden = ch.split(" ")
                    port = iden[1].split(":")
                    nodeid = port[0] + "-" + port[1]
                    if nodeid in neighbor:
                       
                        if nodedetails[nodeid].status == 1:
                            print "Link Up already"
                            break
                        else:
                            datastring = str(listeningport) + " " + "LINKUP"
                            sock3.sendto(datastring, (nodedetails[nodeid].ip , int(nodedetails[nodeid].port)))
                            nodedetails[nodeid].weight = nodedetails[nodeid].previousweight #restoring 
                            nodedetails[nodeid].status = 1 #Link up 
                            nodedetails[nodeid].lastupdate = time.time()
                            oldnodeidindex = -1
                            for i in disvec:
                                oldnodeidindex = oldnodeidindex + 1
                                if flag == 1:
                                    break
                                t = i.split(":")
                                t1 = t[0].split(" ")
                                if t1[1] == nodeid:
                                    lock.acquire()
                                    newdisvec = str(listeningport) + " " + nodeid + ":" +  str(nodedetails[nodeid].weight) + "|"
                                    disvec[oldnodeidindex] = newdisvec
                                    viavec[nodeid] = nodeid
                                    lock.release()
                
                    else:
                        print "Sorry boss! I can only Link up my neighbors. I don't know this guy"
                        
                if "CLOSE" in ch: 
                    print "closing"
                    closedflag = 1 
                   
                    
    
                              
class timerthread(Thread):
    def __init__(self):
        Thread.__init__(self)
        print "timer thread started"
    def run(self): 
        global listeningport 
        global neighbor 
        global disvec
        global disvecbefore 
        global nodedetails 
        global closedflag
        global timeout
        global listeningport 
        sock4 = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        
        while closedflag != 1: 
        
            for i in neighbor:
                if  i in nodedetails and nodedetails[i].status != 0 and int(time.time() - nodedetails[i].lastupdate) > 3*timeout:
                    print "timeout for ", i
                    #connection is closed
                    nodedetails[i].status = 0 #indicates does not exists
                    nodedetails[i].weight = 256
                    datastring = "LINKDOWNSELF" + " " + i
                    nodedetails[i].previousweight = 256
                    nodedetails[i].lastupdate = time.time() # to give some time to delete the data
                    sock4.sendto(datastring, ("127.0.0.1" , int(listeningport)))
                    
                elif i in nodedetails and nodedetails[i].status == 0 and nodedetails[i].previousweight == 256:
                    if int(time.time() - nodedetails[i].lastupdate) > 2*timeout:
                        print "deleting data of", i
                        nodedetails[i].status = 0
                        try:
                            #del nodedetails[i]
                            del viavec[i]
                        except KeyError: 
                            pass
                        try:
                            for k,j in enumerate(disvec):
                                if i in j:
                                    disvec.pop(k)
                        except KeyError:
                            pass
                        try:
                            for k,j in enumerate(neighbor):
                                if i in j:
                                    neighbor.pop(k)
                        except KeyError: 
                            pass
           
                     
                          
                        

                

lock = threading.Lock()   
global closedflag 
closedflag = 0      
global neighbor
global vectorack
global vectordata 
vectorack = {}
vectordata = {}
global listnodes
listnodes = []
global disvec
disvec = []
global weight
global nodedetails 
global viavec #stores next hop value
viavec = {}
global dv
dv = {}        # dv table
global dvlist  #dv of this node 
dvlist = {}     
neighbor = []
weight = []
nodedetails = {}




class node(object):
    def __init__(self,ipaddress,port,weight,previousweight,status,lastupdate):
        
        self.ip = ipaddress
        self.port = port
        self.weight = weight
        self.previousweight = previousweight #restores old weight when link comes up again
        self.status = status #indicates up or down
        self.lastupdate = lastupdate #time since last update message; to check if the client is up      


global listeningport
global timeout
listeningport = int(sys.argv[1])
timeout = int(sys.argv[2])
threads = []

#start getting the neighbors and their ports
i = 3
flag = 0

while flag == 0:

    try:   
        #i gives ip address
        #i+1 gives receiverport
        #i+2 gives weight
        ipaddress = sys.argv[i]
    
        ipport = sys.argv[i+1]
    
        ipweight = sys.argv[i+2]
        clientid = ipaddress + "-" + ipport
    
        neighbor.append(clientid)
        ipnode = node(ipaddress,ipport,ipweight,ipweight,1,time.time())
        nodedetails[clientid] = ipnode
        listnodes.append(clientid)
        strs = str(listeningport) + " " + clientid + ":" + ipweight + "|"
        disvec.append(strs)
        viavec[clientid] = clientid 
        vectorack[clientid] = 0
        vectordata[clientid] = 0
        i = i+3

    except IndexError:
        flag = 1
        if i == 3:
            print "are you sure , no neighbor at all?"
            sys.exit()

    except KeyboardInterrupt:
        sys.exit()
     
    

print "neighbors are ", neighbor 
try:
    newthread = sendthread()
    newthread.daemon = True
    newthread2 = readthread()
    newthread2.daemon = True
    newthread3 = menuthread()
    newthread3.daemon = True
    newthread4 = timerthread()
    newthread4.daemon = True
    newthread.start()
    newthread2.start()
    newthread3.start()
    newthread4.start()
    threads.append(newthread)
    threads.append(newthread2)
    threads.append(newthread3)
    threads.append(newthread4)
   # while True:
    for t in threads:
        t.join(600)
       
    #break        
            
  
            
except KeyboardInterrupt:
    sys.exit()
    
        
        
        







#sock.sendto(packet, (source_ip, clientport))