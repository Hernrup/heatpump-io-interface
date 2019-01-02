# coding=utf-8
import datetime
from string import maketrans
SITE = ""

g_logAll = 0

import sys, os, threading, serial, atexit, datetime, urllib, urllib2, time, struct #, statlink


def setLogAll(v):
    global g_logAll    
    g_logAll = v
    print "---------set var to "+ v



def debugprint (text, level):                               # Log debug information to file and terminal
    now = datetime.datetime.now()
    global g_logAll  
    fname = "tracelog.log"        
    
    # 0 = Log as information
    # 1 = Log as Error
    # 2 = Log as Important information
    # 3 = Log as Initialization info
    
    
    if level == 0:
        t = "INFO:"
                
    elif level == 1:    
        t = "ERROR:"

    elif level == 3:    
        t = "INIT:"
    
    else:
        t = "XINFO:"
    
    
    if level != 9:
        t = t + str(now.time())[0:8]
        t = t + " " + text
    else:
        t=text
    
    if level == 1 or level == 3 or g_logAll == 1: # Logga till fil om ERROR eller om påslaget via kommando
        
    #if level == 1: # Logga till fil om ERROR eller om påslaget via kommando
        try:
            size = os.stat(fname)
            # print("Log file size = " + str(size.st_size))      
            if (size.st_size > 500000): # Max 5 meg för att inte fylla disk
                deletelogfiles ()
        except:	        
		    h=1
			
        try: 
            f = open(fname, 'a')     
            f.write(t + chr(13) + chr(10)) # Till fil
            f.close()
        except:      
            e = sys.exc_info()[1]
            print("Cannot write to logfile: " + str(e) )            
            deletelogfiles ()
            
 
    print(t) # Till konsol
   
     
 


def fileExist (fil):                                        # Check if a file exist
    try:
        f = open(fil,'r')
    except IOError:             
        return 0        
    f.close()    
    return 1        


def sendlogfiles (category, macadress):                               # Send todays logfile to husdata.se
    
    if SITE == "":return
    debugprint("Sending logfile...", 2)                  
    now = datetime.datetime.now()
    fname = "tracelog"                             # File name to open
    
    try:
        f = open(fname + ".log",'r') # Open file and read all to a variable
            ## Read all rows to a variable
    except:
        debugprint("Cannot open file: " + fname + ".log" ,0)  
    else:
        s=""
           
        for line in f:    
            
            if len(line) > 10:
                t = maketrans("\0"," ")
                line = line.translate(t)  # Remove NULL's
                                  
                if (category == "NewDay"): 
                    if (line[0:5] == "ERROR"): s = s + line  # Only send if contains ERROR
                else:
                    if (line[0:5] == "ERROR" or line[0:5] == "XINFO" or line[0:4] == "INIT" or category == "FullLog"): s = s + line                
                
        f.close()
        
                
        if category == "": category = "tracelog"
        
        if s!="":   # if ther is something in log to send
            user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
            header = { 'User-Agent' : user_agent }    
            url=SITE +"/rpicalls/logfiles.asp"
           ## print (s)
            
            values = {
                    'Filename':category + "_" + macadress,
                    'Mac': macadress, 
                    'Data': s
                     }
            data = urllib.urlencode(values)        
            req = urllib2.Request(url, data, header)
            try:       
                w = urllib2.urlopen(req)   # Send data to server
            except:
                e = sys.exc_info()[1]
                debugprint("Cannot reach online service: " + str(e) ,1)  
            else:
                response = w.read()
                w.close()
             
                #print data
                debugprint("Response:" + response,0)                  
    
        
        
def deletelogfiles ():                                      # Delete logfile
    debugprint("Deleting Logfile",2)     
    fname = "tracelog.log"
    
    try:     
        os.remove (fname)
    except:    
        e = sys.exc_info()[1]
        debugprint("Problem to remove logile: " + str(e) ,2)          
     
    

def downloadFile(url, mac):                                 # Download file from URL for upgrade for StatLink
  
    if SITE == "":return
    if len(url) > 5: # 
        
        #Separate filename part
        x=0    
        while url.find("/",x) != -1:
            x = url.find("/",x)
            x=x+1
    
        filename = url[x:]
        
        try: 
            import urllib2
            upgdfile = urllib2.urlopen(SITE+url)
            output = open(filename,'wb')
            output.write(upgdfile.read())
            output.close() 
            debugprint("Downloaded file: " + filename,2)           
            return True
        except:    
            debugprint("Downloading: " + url,2)       
            

def flash_delete():                                         # Delete hex file after succesful startup
    os.remove ("main.hex")
    
def flash(comport):                                         # Write upgrade hex file to PIC controller on H1 interface
       
    #print "comport = " + comport
    com = serial.Serial(comport, baudrate=19200, timeout=0.05) 
    com.close()
    com.open()
    debugprint ("Opened serial port for upgrade: " + com.name, 2)       
    
    Abort = False
    Done = False    
    fname = "main.hex"
    
    
    
    try:
        with open(fname) as f:        
                 
            com.write(chr(13))           # Cleanup            
            com.write("!")               # Enter bootloader (or Enter "FW update mode" if only bootloader working)
            s = com.readline()           # Read response
            if s == "Bootloader...":     # Is it Bootoloader...?
                debugprint("Bootloader entered ok, Upgrading...",2)             # If so all is ok
                com.write("!")                                                  # Enter "FW update mode"
            else:
                debugprint("Already in Bootloader '" + s + "', Upgrading...",2) # No need to send additional ! if no response and already in BL mode
       
                
            HexDataRow = f.readline() # Read first line from HEX file
            r = 1
            while (HexDataRow != "" and Done==False and Abort==False):
                ACK_Received = False
                com.write(HexDataRow.strip() + chr(10)) # Send row to PIC
               
                Counter = time.time() + 2  #2 second timeout, waiting for ACK response from PIC
                while ACK_Received == False and Done==False and Abort==False:      # wait for the ACK from the PIC

                    msg = com.read()  # Read response from PIC (One character)
                    
                    RX = msg.decode("utf-8",errors='ignore')   
                    RX = RX[0:1]    
                    
                    if RX == chr(6): # If ACK
                        ACK_Received = True
                    
                    if HexDataRow[0:1] == ";": # End of file
                        debugprint("Interface upgrade successful, restarting!",0)
                        Done=True
                      
                    elif time.time() > Counter:
                        Abort=True
                        debugprint("No interface response while upgrading, row " + str(r),1)
                        
                    
                if Done==False and Abort==False:    
                    Counter = time.time() + 2 # 2 second timeout
                    HexDataRow = f.readline()  # Read in next row in file
                    r=r+1
                else:
                    f.close()
                   # os.remove (fname)  # Tag bort filen även om det gick dåligt för att inte fastna i en evig omstartsloop
                    
                if Done == True: 
                    os.remove (fname)
                    return 1
   
    
    #else: 
    except IOError:             
        debugprint("Could not open file for H1 upgrade",1)
      
        return 0
    
    return 0   
             
    #time.sleep(.5)    



def upgradeInterface(comport):                              # Perform upgrade of H1 interface
    
    
    if (fileExist("main.hex")):    
        debugprint("Upgrading interface...",2)    
        Tries = 0
        Success = 0
        while Tries < 3 and Success != 1:   # Normal upgrade if main FW is working
            Success = flash(comport)
            Tries = Tries + 1
       
        if Success==0:
            debugprint("Interface upgrade failed!",1)
              
        
#        sys.exit()    # Avsluta StatLink
#    
#    Success = 1
#    while (Success == 1):    
#        debugprint("Upgrading interface...",2)    
#        Tries = 0
#        while Tries < 3 :   # Normal upgrade if main FW is working
#            Success = flash(comport)
#            time.sleep (15)
#
#            Tries = Tries + 1
#     
#        if Success==0:
#            debugprint("Interface upgrade failed!",1)
#            sys.exit()    # Avsluta StatLink
     

    
    
    
def set_wlan(ssid, key):
    debugprint("Setting Wlan to:" + ssid + "   " + key,2)    
    if (os.name == "nt"): return
    
    fc = "\r\n"
    fc = fc + "auto lo\r\n"
    fc = fc + "iface lo inet loopback\r\n"
    fc = fc + "auto eth0\r\n"
    fc = fc + "allow-hotplug eth0\r\n"
    fc = fc + "iface eth0 inet dhcp\r\n\n"
    
    fc = fc + "auto wlan0\r\n"
    fc = fc + "allow-hotplug wlan0\r\n"
    fc = fc + "iface wlan0 inet dhcp\r\n\n"
    
    fc = fc + "wpa-ssid " + ssid + "\r\n"
    fc = fc + "wpa-psk " + key + "\r\n"
    
    fname = "/etc/network/interfaces"
    f = open(fname, 'w') 
    f.write(fc)
    f.close()
    
        