# coding=utf-8
from __future__ import division  # To support floating point division


## -------------------------------------------------------------
## |            Husdata StatLink-PY for Rasbian                |
## |               (C) 2013-2017, Arandis AB                   |
## |           N:a Pitholmsvagen 14, 94146 Pitea               |
## |    Contact: peter@arandis.se, tel. +46 70 6644616         |
## |  Software can be modified for unsupported personal use    |
## |             www.husdata.se, www.arandis.se                |
## ------------------------------------------------------------- 

SITE = ""
VER = "5.0.15"                                     # StatLink RPI version (must be 5 major)

import sys, os, threading, serial, atexit, datetime, urllib, urllib2, time, signal, json, struct, s_io, mqtt

#import s_rrd
from uuid import getnode as get_mac

LF = serial.to_bytes([10])
CR = serial.to_bytes([13])
CRLF = serial.to_bytes([13, 10])

# g_startseq contants
START_INIT    = 0  # 0=Initialisation serial comm, Request Version from Interface (XV)
START_INT_OK  = 2  # 2=Version reponded and HP model identified, Request sensor list (XL) 
START_LIST_OK = 4  # 4=Load sensor list, Request refresh sensors (XR)
START_DONE    = 5  # 5=Normal running state (XR Recieved).   


class ser:                                        # Serial communication
    operatingsys = "Unknown"
    comport = "none"
    portstatus = 0


    """Serial communication"""
    def __init__(self):

        self.inttype = 0
        self.intver = 0
        if os.name == "nt": # Handle Seriaport init differently depending on platform
            self.comport = "COM1" # Windows
            self.operatingsys = "Windows"
            time.sleep (1)
        else:
            self.comport = "/dev/ttyAMA0" # Posix / RPI GPIO
            #self.comport = "/dev/ttyUSB0" # Posix / RPI USB Serial adapter
            self.operatingsys = "Linux"
            s_io.debugprint ("Sleeping 15 seconds...", 2)       
            #time.sleep (15) # Wait so network in PI is started to obtain correct mac adress



    def open(self):
        try:           
            self.com = serial.Serial(self.comport, baudrate=19200, timeout=0.05) 
            self.portstatus = 1
        except:    
            s_io.debugprint("Open com port error (" + self.comport + ")!",1)
            os._exit(0)

        self.com.close
        self.com.open  # Reopen serial port
        s_io.debugprint ("Opened serial port: " + self.com.name, 3)       
        self.com.write(CR) # töm ev skräp

    def openHS(self):
        try:           
            self.com = serial.Serial(self.comport, baudrate=115200, timeout=0.05) 
            self.portstatus = 1
        except:    
            s_io.debugprint("Open com port HS error (" + self.comport + ")!",1)
            os._exit(0)

        self.com.close
        self.com.open  # Reopen serial port
        s_io.debugprint ("Opened serial port HS: " + self.com.name, 2)       
        self.com.write(CR) # töm ev skräp    

    def getS0count(self):
        self.com.write(CR + "SE" + CR) # Request S0 pulses

    def send(self,sendstr):
        if self.portstatus == 1:
            y = str(sendstr)
            self.com.write(CR + y + CR) 
    def reqVersion(self):
        self.com.write(CR + "XV" + CR) # Request interface version        
    def reqReset(self):
        self.com.write(CR + "!")       # Reset interface                    
    def reqStat(self):
        self.com.write("XR" + CR)      # Request Stat refresh dump    


    def reqSetVar(self,Index, Value):
        Value = int(Value)       
        if Value < 0: Value = Value + 0x10000  # format as negative
        xv = str(hex(Value))[2:]
        if len(xv) == 1: xv = "000" + xv
        if len(xv) == 2: xv = "00" + xv
        if len(xv) == 3: xv = "0" + xv
        ss = "XW" + str(Index) + xv            
        s_io.debugprint ("Setting a variable on controller. Index=" + Index + ", Value=" + str(Value) + ", Sendstr= " + ss,2)
        #self.com.write(CR+LF) # Set value of an variable in controller
        self.com.write(ss + CR) # Set value of an variable in controller
        time.sleep(1)
    def reqList(self):
        self.com.write("XL" + CR) # Request List of all possible variables
    def readline(self):
        if self.portstatus == 1:
            return self.com.readline()
    def intVer(self):
        return self.intver
    def intSetVer(self,ver):
        self.intver = ver
    def intType(self):
        return self.inttype
    def intSetType(self,itype):
        self.inttype = itype
    def close(self):
        self.portstatus = 0
        s_io.debugprint ("Closing serial port: " + self.com.name, 2)       
        self.com.close()



def serial_in(indata):                            # Parsing and interpret serial in-data from interface
    global g_startseq    
    global g_interface  
    global g_debugSerial
    global g_exit
    global VER
    hit=0 

    if g_debugSerial and len(indata) > 6: s_io.debugprint(indata , 9)   

    ## XV READ VERSION AND TYPE OF INTERFACE
    if  len(indata) > 6 and indata[0:2] == "XV" and g_startseq == START_INIT:
        hit=1
        # sens = indata[2:6] # Pick out the sensor ID part
        # print (indata)
        vpmod="none"
        g_interface.intSetType (indata[2:4]) # Set global VP id no
        g_interface.intSetVer (indata[4:8])  # Set global id interface FW
        if g_interface.intType() == "00":  vpmod = "Rego 600"
        if g_interface.intType() == "05":  vpmod = "Rego 400"
        if g_interface.intType() == "10":  vpmod = "Rego 2000"
        if g_interface.intType() == "30":  vpmod = "Rego 1000"
        if g_interface.intType() == "35":  vpmod = "Rego 800"
        if g_interface.intType() == "40":  vpmod = "Nibe EB100"
        if g_interface.intType() == "50":  vpmod = "Nibe Styr2002"
        if g_interface.intType() == "60":  vpmod = "Diplomat"
        if g_interface.intType() == "70":  vpmod = "Villa"
        s_io.debugprint("HP Model: " + vpmod + ", Firmware: " + g_interface.intVer(),3)    

        ##s_io.flash_delete
        g_startseq = START_INT_OK # Set to awaiting List mode

        ## XL READ IN SENSOR LIST FROM INTERFACE    
    if  len(indata) > 5 and indata[0:2] == "XL" and g_startseq == START_INT_OK:
        hit=1
        # print (indata)
        if indata[0:6] != "XL EOF":         # IF it is NOT the end of the list
            index = indata[3:7]             # Bring out the index number
            mp.append({"Index": indata[3:7],  # Append Sensor to array
                       "Name": indata[8:], 
                       "Value": 9999,        # Set to default Value
                       "Stat1": 0,           # Not used
                       "Stat2": 0,           # Not Used
                       "Stat3": 0})          # Number of starts


        if indata[0:6] == "XL EOF":         # IF it is the end of the list        
            s_io.debugprint("Sensor list loaded succesfully",2)   # Done
            mp.append({"Index": "EOF"})    

            g_startseq=START_LIST_OK

    ## XR READ DATA UPDATE FROM SENSOR    
    if  len(indata) > 9 and indata[0:2] == "XR" and g_startseq >= START_LIST_OK:
        hit=1

        g_startseq=START_DONE
        sens = indata[2:6] # Pick out the sensor ID part
        val = int("0x" + indata[6:10],0) # Pick out the value part and konvert hex -> int
        hit = 0
        v = val
        mp_ptr=0


        while mp[mp_ptr]["Index"] != "EOF":  ## search for sensor

            if sens == mp[mp_ptr]["Index"]: # Sens ID found

                if sens[0:1] == '0':  # UNIT TEMP #
                    if v & 0x8000: v = v - 0x10000   ## Negative if Highest bit is set           
                    if v == 0x8000: ## No sensor connected
                        v = 0
                        val = 0
                    if v != 0: v=v/10  ## Divide number with 10 to convert to float                
                    valprint=str(v) + "c"

                elif sens[0:1] == '1':  # UNIT STATUS #    
                    if v != 0:
                        valprint = "ON"

                        mp[mp_ptr]["Stat3"] = mp[mp_ptr]["Stat3"] + 1   ## Number of starts
                    else:
                        valprint = "OFF"
                        ##  mp[mp_ptr]["Stat1"] = time.time()   #Store time when put to on

                elif sens[0:1] == '2':  valprint = str(v)  # Number                 
                elif sens[0:1] == '3':                     # Percent
                    if v != 0: v=v/10  ## Divide  to get decimals
                    valprint = str(v) + " %" 
                elif sens[0:1] == '4':  valprint = str(v) + " Amp" 
                elif sens[0:1] == '5':  valprint = str(v) + " kWh"
                elif sens[0:1] == '6':  valprint = str(v) + " hr"
                elif sens[0:1] == '7':  valprint = str(v) + " min"
                elif sens[0:1] == '8':  valprint = str(v) + " c min"
                elif sens[0:1] == '9':  valprint = str(v) + " kw"
                elif sens[0:1] == 'A':  # Electrical meter, Pulses 
                    if (mp[mp_ptr]["Value"] == 9999):  mp[mp_ptr]["Value"] = 0  # Uppstart

                    val = mp[mp_ptr]["Value"]  + val
                    valprint = str(v) + " Pulses, tot(" + str(val) + ")"


                # UNKNOWN UNIT ##                        
            else:                   valprint = indata[6:10]

            #now = datetime.datetime.now()    
            s_io.debugprint (mp[mp_ptr]["Name"] + " = " + valprint,0)
            mp[mp_ptr]["Value"] = val
            hit = 1

            mqtt_.publish(sens,v)

            break 

        mp_ptr = mp_ptr + 1  # Increase mp pointer


    ## SP S0 PULSES UPDATE
    if  len(indata) > 4 and indata[0:2] == "SP" :        
        hit=1
        #s_io.debugprint ("S0 Pulses: " + indata,0)    

        S0_1 = int("0x" + indata[2:6],0) # Pick out the value part and konvert hex -> int
        #S0_2 = int("0x" + indata[6:10],0) # Pick out the value part and konvert hex -> int

        s_io.debugprint ("S0_1=" + str(S0_1),0)    


    ## XE LOG H1 ERROR MESSAGE 
    if  len(indata) > 4 and indata[0:2] == "XE" :        
        hit=1
        s_io.debugprint ("H1 Interface error: " + indata,1)

    ## XM LOG H1 INFO MESSAGE     
    if  len(indata) > 4 and indata[0:2] == "XM" :        
        hit=1
        s_io.debugprint ("H1 Message: " + indata,2)        
        if  indata[0:5] == "XM900" :        # V-List
            g_startseq = START_DONE         # Disable all request meanwhile
            g_interface.close()  
            g_interface.openHS()            # Open port in HighSpeed mode
            g_debugSerial=True              # Enable Serial data full log

        if  indata[0:5] == "XM901" :               # V-List complete
            s_io.sendlogfiles ("FullLog",g_mac)    # Send log
            s_io.deletelogfiles()            
            g_interface.reqReset()                 # reset interface
            g_exit = True                          # restart RPI

    ## DETECT AND CORRECT MISSING FIRMWARE
    if  len(indata) > 9 and indata[0:10] == "Bootloader" and g_startseq == START_INIT:
        hit=1
        s_io.debugprint ("Firmware missing", 1 )
        VER = "5.0.0"


    ## LOG UNHANDLED H1 DATA OUTPUT
    if  len(indata) > 4 and hit==0:        
        s_io.debugprint ("H1 RX: " + indata,2)



# ===========================================================

class Online:                                     # Storing stat data to var and sends to Portal every 6 min, Aslo check for upgrades and settings changes.
    sendbuf = ""   # Init var
    mincount = 6   # Init var
    errorcounter = 0
    global g_mac
    global g_interface

    def converttemp(self, temp):
        if temp & 0x8000: temp = temp - 0x10000   ## Negative if Highest bit is set           
        if temp == 0x8000: temp = 0 ## No sensor connected
        if temp != 0: temp=temp/10  ## Divide number with 10 to convert to float        
        return temp

    def webstat(self):
        m=0
        outdoor=0
        indoor=0
        while mp[m]["Index"] != "EOF":  ## search for sensor
            if mp[m]["Value"] != 9999:
                if mp[m]["Index"] == "0002":  # 0007
                    outdoor = mp[m]["Value"] 
                    outdoor = self.converttemp(outdoor)
                if mp[m]["Index"] == "0009":  # 0008
                    indoor = mp[m]["Value"]
                    indoor = self.converttemp(indoor)
            m=m+1    


        #s_rrd.rrd_update(outdoor,indoor)
        #  s_rrd.rrd_update(3,22)

    def minStat(self):   # Run every minute

        s=""
        self.mincount = self.mincount + 1
        now = datetime.datetime.now()
        t = str(datetime.date(now.year,now.month,now.day)) + " " + str(datetime.time(now.hour, now.minute, now.second))
        s = "<StatCollection>" # Build XML stat data string
        s = s + "<Time>" + t + "</Time>"
        #print self.mincount
        mp_ptr = 0
        while mp[mp_ptr]["Index"] != "EOF":  ## search for sensor
            if mp[mp_ptr]["Value"] != 9999:
                s = s + "<StatItem>"

                s = s + "<ID>" + str(mp[mp_ptr]["Index"]) + "</ID>"
                s = s + "<SID>" + str(50) + "</SID>"
                #s = s + "<Value>" + str(mem[i]) + "</Value>"
                v = mp[mp_ptr]["Value"]            
                if mp[mp_ptr]["Index"][0:1] == "1": # If Status type
                    if v==1:
                        v = 60  # 60 sek per minute if device is active
                        mp[mp_ptr]["Stat3"] = mp[mp_ptr]["Stat3"] + 60   # Add 60 seconds to runtime

                elif mp[mp_ptr]["Index"][0:1] == "A": # If Electrical meter acumulated pulses
                    mp[mp_ptr]["Value"] = 0   # Zero pulse counter

                else:
                    if v & 0x8000: v = v - 0x10000   # Negative if Highest bit is set          
                s = s + "<Value>" + str(v) + "</Value>"
                s = s + "</StatItem>"
            mp_ptr = mp_ptr + 1

        s = s + "</StatCollection>"    

        self.sendbuf = self.sendbuf + s
        s_io.debugprint ("Stat written to var!  " + str(self.mincount) + "  " + str(len(self.sendbuf)),0) 

        self.webstat()




    def uploadStat(self):   # Run every 5 minute
        global g_exit   
        global VER
        global g_wd_lastTimeOk
        global g_commEnabled 

        if g_commEnabled == 0:  # Skip all if no online account
            self.mincount = -10
            self.sendbuf = "" # nollställ
            g_wd_lastTimeOk = datetime.datetime.now()     # Reset watchdog so no auto reboot
            s_io.debugprint("Abortin online comm.. communications is disabled" ,0)


        if self.mincount > 4 and g_commEnabled == 1:  ## For each 5:e minute, compile XML stat data string and upload to portal.                   
            user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
            header = { 'User-Agent' : user_agent }    
            url = SITE + "/rpicalls/statdata514.asp"        

            now = datetime.datetime.now()      
            t = str(datetime.date(now.year,now.month,now.day)) + " " + str(datetime.time(now.hour, now.minute, now.second))        

            s =     "<?xml version=" + chr(34) + "1.0" + chr(34) +" ?>" 
            s = s + "<StatCast>"
            s = s + "<CreateTime>" + t + "</CreateTime>"
            s = s + "<User>" + g_mac + "</User>"
            s = s + "<CheckSum>283086228</CheckSum>"  # Not implemented yet
            s = s + "<Version>" + VER + "</Version>"
            s = s + self.sendbuf 

            values = {
                'Mac': g_mac, 
                'Data': s, 
                'SL_ver': VER, 
                'H1_ver': g_interface.intType() + g_interface.intVer(),
            }

            data = urllib.urlencode(values)        
            req = urllib2.Request(url, data, header)
            #print data
            #print s
            try:       
                f = urllib2.urlopen(req)
                response = f.read()         # Response from webserver in JSON format
                #print response
                data = json.loads(response) # Decode JSON to Dict            
            except:
                e = sys.exc_info()[1]
                s_io.debugprint("Call:" + url,2)            
                self.errorcounter = self.errorcounter + 1                
                s_io.debugprint("Internet unreachable: (" + str(self.errorcounter) + ") " + str(e) ,2)
                if (self.errorcounter >= 4 ): # Restart unit after 4 (20min) failures to reach the internet
                    s_io.debugprint("Internet unreachable, rebooting...", 1)  
                    g_exit = True  # Terminate all timer threads and exiting                

            else:

                #print data  # Debug print of response from webserver
                if data["Response"] == "OK":# StatUpload was OK
                    self.errorcounter = 0   # Reset restart if no online access
                    if len(data["WifiSSID"]) > 0:
                        s_io.set_wlan(data["WifiSSID"], data["WifiKeyPass"])
                        s_io.debugprint("Wifi credentials set, restarting....", 2)  
                        g_exit = True  # Terminate all timer threads and exit to reboot                                        

                    # commands for debug and troubleshooting
                    ## resetlog  Send logfile (INFO aswell) and remove old log
                    ## restart   Send logfile and restart RPI
                    ## debug     Turn on/off detailed serial logging
                    ## logall    Turn on full logging to textfile
                    ## H1cmd|xx  Send command xx to H1 interface

                    if len(data["Cmd"]) > 0:
                        if (data["Cmd"] == "resetlog") :                #    resetlog
                            s_io.sendlogfiles ("FullLog",g_mac)   
                            s_io.deletelogfiles()

                        if (data["Cmd"] == "upgrade") :                #    Re-read software and upgrade
                            VER = "5.0.0"

                        if (data["Cmd"][0:5] == "H1cmd") :              #    H1cmd|xxxxx
                            v = data["Cmd"].split('|') 
                            s = "Sending: " + v[1] + " to interface"
                            s_io.debugprint(s, 2)  
                            g_interface.send(v[1])

                        if (data["Cmd"][0:5] == "logall") :              #    Log all to file for debug ON, restart to reset to 0
                            s_io.setLogAll(1)          
                            s_io.debugprint("Log All to file ON", 2)                              

                        if (data["Cmd"][0:5] == "debug") :              #    debug
                            if (g_debugSerial==True) :                      
                                g_debugSerial=True          
                                s_io.debugprint("Serial Debug ON", 2)  
                            else :
                                g_debugSerial=False  
                                s_io.debugprint("Serial Debug OFF", 2)                            

                        if (data["Cmd"] == "restart") :                 #    restart
                            s_io.debugprint("StatLink was shutdown on demand...", 2)  
                            s_io.sendlogfiles ("ExitReboot",g_mac) 
                            g_exit = True  # Terminate all timer threads and exiting

                    s_io.debugprint("Stat Data recieved OK, Len= " + str(data["Len"]) ,2)
                    g_wd_lastTimeOk = datetime.datetime.now()    

                    if os.name != "nt": # If local developer machine, don't replace files!
                        # Upgrade Statlink and or H1?
                        sl1 = s_io.downloadFile(data["NySL1"], g_mac)
                        sl2 = s_io.downloadFile(data["NySL2"], g_mac)
                        sl3 = s_io.downloadFile(data["NySL3"], g_mac)
                        sl4 = s_io.downloadFile(data["NySL4"], g_mac)
                        sl5 = s_io.downloadFile(data["NySL5"], g_mac)
                        s_io.downloadFile(data["NyH1"], g_mac)

                        if sl1 or sl2 or sl3 or sl4 or sl5:
                            s_io.debugprint("StatLink was upgraded, restarting....", 2)  
                            g_exit = True  # Terminate all timer threads and exiting
                        else:
                            s_io.debugprint("Upgrade availible but skipped, running on dev env.!",2) 


                if data["Response"] == "ERROR":# StatUpload gave ERROR

                    # s_io.debugprint("Error response from Online service: (" + str(self.errorcounter) + ") " ,1)
                    if data["ErrNo"] == "1":
                        g_commEnabled = 0 # Disable communications.
                        s_io.debugprint("Disabled communications" ,1)

                    s_io.debugprint("Error response from Online service: " + data["Descr"] ,1)
                    self.errorcounter = self.errorcounter + 1
                    if (self.errorcounter >= 4 ):  # Restart unit after 4 (20min) failing service requests
                        s_io.debugprint("Online service wrong response, rebooting...", 1)  
                        g_exit = True  # Terminate all timer threads and exiting
                    else:    
                        if len(data["ChangeArray"]) > 4: # Controller variable requested to change

                            w = data["ChangeArray"].split('@') # Array of variables to uppdate
                        i=1
                        while i < len(w):
                            #s_io.debugprint ("Request to change variable recieved:" + str(i) + " " + w[i],2) 
                            z = w[i].split('|') 
                            if z[0] == "UPDATE": g_interface.reqSetVar(z[1],z[2])
                            if z[0] == "CONFIRMED": s_io.debugprint ("Changed variable confirmed! " + z[1],2)
                            i=i+1

                f.close()

                #s_io.debugprint("Response:" + response,2)            

            self.sendbuf = "" # nollställ
            self.mincount = 0



class EverySecond:                                # Event scheduler
    now = datetime.datetime.now()   # Bring todays date/time    
    newDay = str(now.date())        # Init,  day change     (static var)
    newMinute = now.minute          # Init,  minute change  (static var)
    newHour = now.hour              # Init,  hour chamge    (static var)
    onlineStat = Online()

    global g_startseq    
    global g_commEnabled

    initTries = 0
    RunOnceAfterInit = 0

    #def __init__(self):

    def sec(self):   # Run every second 
        global g_exit            
        if g_exit == True: return()

        # NEW SECOND 
        if g_startseq != START_DONE:  
            self.Startup()
        elif self.RunOnceAfterInit == 0:
            s_io.sendlogfiles ("StartUpDone",g_mac)          # Send logfile to Husdata at startup to be able to give support    
            self.RunOnceAfterInit = 1

        #s_io.debugprint("One sec",0)
        now = datetime.datetime.now()
        #g_interface.getS0count()

        # NEW MINUTE 
        if self.newMinute != now.minute: 
            self.newMinute = now.minute            
            if g_startseq == START_DONE: self.onlineStat.minStat()    # Logg HP stat data to variable in XML, only if interface is initialized
            self.onlineStat.uploadStat()                              # Send to portal, check for upgrades and settings change (Every 5 minute)
            mqtt_.reconnect()


        # NEW DAY 

        if self.newDay != str(now.date()) and g_commEnabled == 1: # If date has changed
            s_io.debugprint("New day detected:" + self.newDay + "   " + str(now.date()),0)
            self.newDay = str(now.date())            
            s_io.sendlogfiles ("NewDay",g_mac)      # Send logfile to Online system if it contatins error records
            s_io.deletelogfiles()                   # Remove logfile after it has been sent


        # NEW HOUR 
        if self.newHour != now.hour: 
            self.newHour= now.hour            
            s_io.debugprint("Requesting hourly refresh of all registries",0)
            if g_startseq == START_DONE: g_interface.reqStat() # Request refresh-data from interface every hour to avoid miss sync for any reason   


        threading.Timer(1.0, self.sec).start()   # Reinitialize timer and run again in 1 sec        


    def Startup(self):                         # Secure start up of all communication
        global g_exit
        if self.initTries > 180: 
            s_io.debugprint("Could not initilize within 3 minutes, rebooting...",1)        
            g_interface.reqReset()  # Reset interface
            s_io.sendlogfiles ("ExitReboot", g_mac)          # Send todays logfile to Husdata at start to be able to give support
            g_exit = True

        if g_startseq == START_INIT:   # If no H1 version response
            g_interface.reqVersion()   # Ask interface of version
            s_io.debugprint("Requesting interface version...",3)
            self.initTries=self.initTries+1

        if g_startseq == START_INT_OK:   # If no H1 List read
            g_interface.reqList() # Request List
            s_io.debugprint("Requesting sensor list...",3)
            self.initTries=self.initTries+1

        if g_startseq == START_LIST_OK:   # If no H1 data in
            g_interface.reqStat() # Request refresh-data from interface    
            s_io.debugprint("Requesting sensor data dump",3)
            self.initTries=self.initTries+1


def signal_handler(signal, frame):                # Close script at Ctrl-C 
    g_exit=True
    os._exit(0)

def rx_thread ():                                 # Recieve serial data in separate thread

    global g_interface
    global g_rxbuf
    global g_rxbufptr    

    if g_interface.portstatus == 1:
        try:
            msg = g_interface.readline()  # Read data to cr/lf
            d = msg.decode("utf-8",errors='ignore') ## Decode from byte to str  (errors='replace')                
            d = str(d).strip()    ## Remove cr, lf and spaces in the beginning and end of string

            if d != "" :
                ##g_rxbuf[g_rxbufptr] = d
            ##g_rxbufptr = g_rxbufptr + 1
            ##print  str(g_rxbufptr) + "+" + str(d  )
            serial_in(d) # Manage incoming data from interface


        except:
            d = ""   

        thread = threading.Thread(target = rx_thread)
        thread.start()    

def main():                                       # Main start / init and loop

    global g_startseq   
    global g_debuglevel
    global g_interface
    global g_mac
    global mp
    global g_wd_previous
    global g_wd_current
    global g_wd_lastTimeOk
    global g_exit
    global g_debugSerial
    global g_rxbuf
    global g_rxbufptr
    global VER
    global g_commEnabled
    global mqtt_

    mp = []                        # The struct with all sensors and values
    g_debuglevel = 1               # Printout debugdata to console
    g_startseq = START_INIT        # Start up steps, initialization sequence status
    g_wd_current = 0               # Watchdog
    g_wd_previous = 1              # Watchdog
    g_wd_lastTimeOk = datetime.datetime.now()   # Watchdig
    g_exit = False                 # Killing timers if True.
    g_debugSerial = False
    g_rxbuf = [0,0,0,0,0,0,0,0,0,0]
    g_rxbufptr = 0
    g_commEnabled = 1              # Set to 0 if no online accound active to prevent retries
    g_mqtt_status = 1		   # Enabled      

    s_io.debugprint("    " ,2)    
    s_io.debugprint("StatLink start. Version: " + VER,3)    

    #for arg in sys.argv:
    #        print arg

    # Check if any command line arguments given    
    if (len(sys.argv) > 1):
        if (sys.argv[1] == "-u"):
            s_io.debugprint("Update",2)       
            VER = "5.0.0"

        if (sys.argv[1] == "-d"):
            g_debugSerial=True          
            s_io.debugprint("Serial Debug ON", 2)              

    signal.signal(signal.SIGINT, signal_handler)   # Listen after Ctrl-C
    g_interface = ser()           # Initialize serial port and class

    #signal.pause()


    # Get hardware mac address -------
    if (os.name == "nt"):
        g_mac = hex(get_mac())[2:]          # Get the Windows computers MAC address
        if len(g_mac) < 12:                 # If mac address is leading 00 it is stripped and has to be replaced
            g_mac = "00" + g_mac

    else:
        g_mac = open('/sys/class/net/eth0/address').read()  # Get the RPI units MAC address for identification
        g_mac = g_mac.replace(":","")

    g_mac = g_mac [:-1]
    s_io.debugprint ("MAC adress: " + g_mac ,2)

    s_io.sendlogfiles ("StartUpInit",g_mac)          # Send logfile to Husdata at start to be able to give support        

    s_io.upgradeInterface(g_interface.comport)       # Upgrade interface if hex file exist

    g_interface.open()                 # Open serial port    

    if SITE == "": g_commEnabled = 0

    # MQTT CLIENT INIT
    mqtt_ = mqtt.Mqtt_comm() # init class
    mqtt_.init()
    mqtt_.connect()

    EverySec = EverySecond()           # Initialize EverySec class
    EverySec.sec()                     # Run Every Sec

    rx_thread()                        # Start serial receiever thread

    char = ""    
    while g_exit == False: # Eternal loop until Ctrl-C

        ##msg = g_interface.readline()
        ##d = msg.decode("utf-8",errors='ignore') ## Decode from byte to str  (errors='replace')
        time.sleep    (0.1)
        #    serial_in(d) ## Manage incoming data from interface
    ##    if d != "":
    ##     print (d)
    ##        serial_in(d) ## Manage incoming data from interface

    if g_rxbufptr > 0:  # Manage incoming data from interface
        i=0

        print "     " + str(g_rxbufptr) + "-" + str(g_rxbuf[i]).strip()
        serial_in(g_rxbuf[i]) # Manage incoming data from interface
        while (i < g_rxbufptr):
            g_rxbuf[i] = g_rxbuf[i+1]
            i=i+1
            g_rxbufptr = i-1


        g_wd_current = g_wd_current + 1
        if g_wd_current > 10: # Once a second approx..
            g_wd_current = 0


            now = datetime.datetime.now()
            wa = datetime.datetime(now.year,now.month,now.day,now.hour,now.minute,now.second)    
            wb = datetime.datetime(g_wd_lastTimeOk.year,g_wd_lastTimeOk.month,g_wd_lastTimeOk.day,g_wd_lastTimeOk.hour,g_wd_lastTimeOk.minute,g_wd_lastTimeOk.second)    
            wx = (wa - wb).total_seconds()
            #print wx
            if (wx > 3600 and g_commEnabled != 0): # en timme
                s_io.debugprint("Watchdog termination, no online response in 1 hour.",2)    
                os._exit(0)
        # char = sys.stdin.read(1)    



    # Exit StatLink to OS    
    s_io.debugprint ("StatLink terminated!",2) 
    g_interface.close() # close serial port
    os._exit(0)


if __name__ == "__main__":
    main()






