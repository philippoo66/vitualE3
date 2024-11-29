"""
   Copyright 2023 philippoo66
   
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

"""
version 1.0.3:
    more issues regarding multi ECU fixed

version 1.0.2:
    some bugs fixed

version 1.0.1:
    args issue fixed

version 1.0.0:
    multi-ECU via json devices file

version 0.9.10:
    overlay simulation data if no device specific dataIdentifiers

version 0.9.9:
    no ECU Addr in datapoints.py

version 0.9.8:
    dids not in dicE3 randomly inited only once    
    multiple padding fixed

version 0.9.7:
    dyndata implemented
    dicE3 static random values if no simulation data

version 0.9.6:
    wr timeout depending on dlen
    check PCI on write multi
    
version 0.9.5:
    dynamic did list module import implemented

version 0.9.4:
    switch for universal list version implemented

version 0.9.3:
    wirting data impemented

version 0.9.2:
    read E3 data from raw scan and use them

version 0.9.1:
    init/reset multilen = 0 on RDBI reception
"""

import can          # https://pypi.org/project/python-can/
import argparse
import time
import threading
import random
import importlib
import os
import json

import Open3Edatapoints


filters = []
channel = 'vcan0'
txdata = bytes()
rxdata = bytes()
wrdid = 0

# RDBI multi frame control 
multiptr = 0
multilen = 0
multipci = 0x20

# com state machine
comstate = 0

# current request/device
currCob = 0

# dict of ecus
dicEcus = {}  # addr:[dataIdentifiers,dicSimulData]

dyndata = {}


# read simulation data ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def readsim(file):
    dicdata = {}
    if os.path.exists(file):
        with open(file, 'r') as file:
            lines = file.readlines()

        for line in lines:
            buffer = line.strip().split()    # (';') for csv

            if not buffer[0].isdigit():
                continue  # Überschriftenzeile und Kommentare überspringen

            did = int(buffer[0])
            data = bytes.fromhex(buffer[1])
            dicdata[did]=data

    return dicdata


def make_ecu(addr:int, dev:str, simdata:str) -> list:
    dids = {}
    sims = {}
    if(dev != None):
        if('.py' in dev):
            module_name = dev.replace('.py', '')
        else:
            module_name = "Open3Edatapoints" + dev.capitalize()
        # load datapoints for selected device
        didmoduledev = importlib.import_module(module_name)
        dids = didmoduledev.dataIdentifiers["dids"]
    if(simdata != None):    
        sims = readsim(simdata)
    return [dids,sims]


# utils ~~~~~~~~~~~~~~~~~~~~~~~
def getint(v) -> int:
    if type(v) is int:
        return v
    else:
        return int(eval(str(v)))


def shex(nbr:int) -> str:
    return format(nbr, '03x')


# timeout +++++++++++++++++++++++++++++++++++++++
def on_timout():
    global comstate
    print("Timeout", comstate)
    comstate = 0

timer_tout = threading.Timer(1.0, on_timout)

def startToutTimer(secs:float):
    global timer_tout
    timer_tout.cancel()
    timer_tout = threading.Timer(secs, on_timout)
    timer_tout.start()
    

# sub defs +++++++++++++++++++++++++++++++++++++++

def getTxData(ecu, did:int, init=False) -> bytes:
    dataIdentifiers,dicSimulData = ecu
    regarddyn = False 
    if(not (did in dicSimulData)):
        regarddyn = (len(dynData) > 0)
        if(not init): 
            print(f"random: {hex(addr)}, {did}")
        dicSimulData[did] = bytes([random.randint(0x20, 0x7E) for _ in range(dataIdentifiers[did].string_len)])  # printable ASCII

    buffer = dicSimulData[did]
    if(args.dyn or regarddyn):
        if(did in dynData):
            for itm in dynData[did]:
                dystart, dylen, dytype = itm  # extract informations
                print("H", dystart, dylen, dytype)
                if(isinstance(dytype, list)):  
                    dybuff = bytes([random.randint(dytype[0], dytype[1]) for _ in range(dylen)])
                elif(dytype.upper() == 'F'):  # full range 
                    dybuff = bytes([random.randint(0x00, 0xff) for _ in range(dylen)])
                elif(dytype.upper() == 'N'):  # numbers 0..9 
                    dybuff = bytes([random.randint(0x30, 0x39) for _ in range(dylen)])
                elif(dytype == 'L'):  # letters, upper case
                    dybuff = bytes([random.randint(0x41, 0x5A) for _ in range(dylen)])
                elif(dytype == 'l'):  # letters, lower case
                    dybuff = bytes([random.randint(0x61, 0x7A) for _ in range(dylen)])
                else:  # printable ASCII
                    dybuff = bytes([random.randint(0x20, 0x7E) for _ in range(dylen)])

                # Convert buffer to a bytearray, update the section, and then convert back to bytes
                buffarr = bytearray(buffer)
                buffarr[dystart:dystart+dylen] = bytearray(dybuff)
                buffer = bytes(buffarr)

    return buffer


def rdbiRequestReceived(ecu,did,msg):
    global comstate
    global multilen
    global multiptr
    global txdata
    
    txdata = getTxData(ecu, did) + bytes([0x55] * 6)  # padding, max 6 bytes
    dlen = ecu[0][did].string_len

    if(dlen <= 4):
        # single frame, send resonse
        buffer = bytes([dlen+3, 0x62, msg.data[2], msg.data[3]]) + txdata[:4]
        txmsg = can.Message(
            arbitration_id=msg.arbitration_id + 0x10,
            data=buffer,
            is_extended_id=False
        )
        bus.send(txmsg)
        
    else:
        # multi frame, send first frame of response, 3 bytes data
        buffer = bytes([0x10, dlen+3, 0x62, msg.data[2], msg.data[3]]) + txdata[:3]
        multilen = dlen
        multiptr = 3

        txmsg = can.Message(
            arbitration_id=msg.arbitration_id + 0x10,
            data=buffer,
            is_extended_id=False
        )
        bus.send(txmsg)
        comstate = 1
        startToutTimer(0.667) 


def sendRemainReadData(msg):
    global comstate
    global multilen
    global multiptr
    global multipci
    global txdata

    # stop timeout timer
    timer_tout.cancel()
    
    # evaluate separation time
    septm = int(msg.data[2])
    if(septm == 0):
        septm = 50  # ms

    # send data
    while(multiptr < multilen):
        multipci += 1
        if(multipci > 0x2F):
            multipci = 0x20
        
        buffer = bytes([multipci]) + txdata[multiptr:multiptr+7]
        multiptr += 7
        
        txmsg = can.Message(
            arbitration_id=msg.arbitration_id + 0x10,
            data=buffer,
            is_extended_id=False
        )
        time.sleep(septm/1000)
        bus.send(txmsg)
    
    # done
    comstate = 0


def wdbiRequestReceived(ecu, did, msg):
    global comstate
    global rxdata
    global wrdid

    # TODO? check formal

    dlen = ecu[0][did].string_len

    if(dlen <= 4):
        # apply data
        ecu[1][did] = msg.data[4:4+dlen]
        # send confirm
        buffer = bytes([0x03, 0x6E, msg.data[2], msg.data[3]]) + bytes([0x55] * 4)
        txmsg = can.Message(
            arbitration_id=msg.arbitration_id + 0x10,
            data=buffer,
            is_extended_id=False
        )
        bus.send(txmsg)
 
    else:
        # apply data of FF 
        rxdata = msg.data[5:8]
        wrdid = did
        to = dlen * 0.015  # 15ms/byte
        if(to < 1.0): to = 1.0
        # send FC
        buffer = bytes([0x30, 0x00, 0x50]) + bytes([0x55] * 5)
        txmsg = can.Message(
            arbitration_id=msg.arbitration_id + 0x10,
            data=buffer,
            is_extended_id=False
        )
        bus.send(txmsg)
        comstate = 2
        startToutTimer(to)


def receiveRemainWriteData(ecu, msg):
    global comstate
    global multipci
    global rxdata
    global wrdid
   
    multipci += 1
    if(multipci > 0x2F):
        multipci = 0x20

    if(multipci != msg.data[0]):
        print("CF missed:", multipci)
        comstate = 0

    rxdata += msg.data[1:8]
    dlen = ecu[0][wrdid].string_len
    
    if(len(rxdata) >= dlen):
        # receive complete, apply data
        timer_tout.cancel()
        ecu[1][wrdid] = rxdata[0:dlen]
        # send confirm
        buffer = bytes([0x03, 0x6E, (wrdid >> 8) & 0xFF, wrdid & 0xFF]) + bytes([0x55] * 4)
        txmsg = can.Message(
            arbitration_id=msg.arbitration_id + 0x10,
            data=buffer,
            is_extended_id=False
        )
        bus.send(txmsg)
        comstate = 0
        

# ++++++++++++++++++++++++++
# main
# ++++++++++++++++++++++++++

# command line arguments +++++++++++++++++++++++++++++++++++++++
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--can", type=str, help="use can device, e.g. can0")
parser.add_argument("-dev", "--dev", type=str, help="boiler type --dev vdens or --dev vcal or --dev vx3 or --dev vair")
parser.add_argument("-old", "--old", action='store_true' , help="-old for not universal list")
parser.add_argument("-dyn", "--dyn", action='store_true' , help="-dyn for dynamic values")
parser.add_argument("-a", "--all", action='store_true', help="respond to all COB-IDs")
parser.add_argument("-addr", "--addr", type=int, help="ECU address")
parser.add_argument("-cnfg", "--config", type=str, help="json configuration file")
args = parser.parse_args()

if(args.can != None):
    channel = args.can
    
if(args.addr == None):
   args.addr = 0x680


if(os.path.exists('virtdyndata.py')):
    import virtdyndata
    dynData = virtdyndata.dyndata


# make ecu(s) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
if(args.config != None):
    if(args.config == 'dev'):  # short
        args.config = 'devices.json'
    # get configuration from file
    with open(args.config, 'r') as file:
        devjson = json.load(file)
    # make ECU list
    for device, config in devjson.items():
        addr = getint(config.get("tx"))
        dplist = config.get("dpList")
        ecu = make_ecu(addr, dplist, "virtdata_" + shex(addr) + ".txt")
        dicEcus[addr] = ecu
elif(args.dev != None):
    # read device related dataidentifiers
    sdev = args.dev.capitalize()
    ecu = make_ecu(args.addr, sdev, "virtdata" + sdev + ".txt")
    dicEcus[args.addr] = ecu


if(args.all):
    gendids = dict(Open3Edatapoints.dataIdentifiers["dids"])
    sims = {}
    dicEcus[0xfff] = [gendids,sims]


# make dataIdentifiers_dev
if(not args.old):
    print("featuring universal list")
    for key,itml in dicEcus.items():
        dids = itml[0]
        sims = itml[1]
        # load general datapoints table
        gendids = dict(Open3Edatapoints.dataIdentifiers["dids"])
        lstpops = []
        if(len(dids) > 0):
            # add dids to gendids if not contained
            for did,cdc in dids.items():
                if not(did in gendids):
                    gendids[did] = cdc
            # overlay device dids over general table 
            for did in gendids:
                if not(did in dids):
                    if not (did in sims):
                        lstpops.append(did)
                elif(dids[did] != None):  # apply len from dev spcfc
                    gendids[did] = dids[did]        
        # elif(len(sims) > 0):
        #     # overlay simulation data set
        #     for did in gendids:
        #         if not (did in sims):
        #             lstpops.append(did)
        # remove dids not existing with the device
        for itm in lstpops:
            gendids.pop(itm)
        # apply to ecu
        itml[0] = gendids
        # debug only - see what we have now with this device
        #for itm in gendids:
        #    print(f"{itm}:{type(gendids[itm]).__name__}")
        # probably useless but to indicate that it's not required anymore


for addr,lsts in dicEcus.items():
    print(f"{hex(addr)} dids/data: {len(lsts[0])}/{len(lsts[1])}")

# init data by random, regarding dyn range/s if applicable
for addr,ecu in dicEcus.items():
    # init only if no simulation data
    if (len(ecu[1]) == 0):
        for did in ecu[0]:
            ecu[1][did] = getTxData(ecu, did, init=True)

print("ready to go.")

# main loop ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
try:
    with can.Bus(interface='socketcan', channel=channel, receive_own_messages=False, can_filters=filters) as bus:
        # iterate over received messages
        for msg in bus:
            if(comstate == 0): # idle
                currCob = msg.arbitration_id
                if(currCob in dicEcus):
                    ecu = dicEcus[currCob]
                elif(args.all):
                    ecu = dicEcus[0xfff]
                else:
                    # do nothing
                    continue

                # SF or FF of multi
                if((msg.data[0] & 0xF0) == 0):
                    sididx = 1
                elif((msg.data[0] & 0xF0) == 0x10):
                    sididx = 2
                else:
                    continue
                
                if(msg.data[sididx] in [0x22,0x2E]):
                    # RDBI or WDBI request
                    did = int.from_bytes(msg.data[sididx+1:sididx+3], byteorder="big", signed=False)

                    if(not (did in ecu[0])):
                        # DID not existing, send Negative Response 'Conditions not correct' 
                        txmsg = can.Message(
                            arbitration_id=msg.arbitration_id + 0x10,
                            data=[3, 0x7F, msg.data[sididx], 0x22, 0x55, 0x55, 0x55, 0x55],
                            is_extended_id=False
                        )
                        bus.send(txmsg)

                    elif(msg.data[sididx] == 0x22):
                        rdbiRequestReceived(ecu, did, msg)

                    elif(msg.data[sididx] == 0x2E):
                        wdbiRequestReceived(ecu, did, msg)

                    multipci = 0x20

            elif(comstate == 1): # waiting for FC to send remaining read_data
                if((msg.arbitration_id == currCob) and (msg.data[0]==0x30)):
                    # flow control received, send remaining data
                    sendRemainReadData(msg)
 
            elif(comstate == 2): # waiting for remaining write_data
                if(msg.arbitration_id == currCob):
                    receiveRemainWriteData(ecu, msg)

except (KeyboardInterrupt, InterruptedError):
    # got <STRG-C> or SIGINT (<kill -s SIGINT pid>)
    #pass
    print(" done")
                        
                        
                        
