from __future__ import division  # To support floating point division
import logging
import threading
import time
import os
import enum

logger = logging.getLogger(__name__)

def run():                                       # Main start / init and loop
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
    g_mqtt_status = 1

    s_io.debugprint("    " ,2)    
    s_io.debugprint("StatLink start. Version: " + VER,3)    

    signal.signal(signal.SIGINT, signal_handler)   # Listen after Ctrl-C
    g_interface = ser()           # Initialize serial port and class
    g_interface.open()                 # Open serial port    

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

    # Exit StatLink to OS    
    s_io.debugprint ("StatLink terminated!",2) 
    g_interface.close() # close serial port
    os._exit(0)

def run2():
    signal.signal(signal.SIGINT, signal_handler)   # Listen after Ctrl-C
    client = Client()

    client.connect()

    mqtt_handler = MqttHandler(client)
    mqtt_handler.connect()

    # client.add_callback(mqtt_handler.publish)

    client_worker = ClientWorker(client)
    client_worker.connect()

    client_worker.start()
    # mqtt_handler.start()

    client_worker.stop()
    client_handler.join()

    # mqtt_handler.stop()


class ClientState(enum.Enum):
    INIT    = 0  # 0=Initialisation serial comm
    OK    = 5  # 5=Normal running state


class Client:

    def __init__(self, port=None):
        self.port = port
        self.model = None
        self.sensors = None

        if not port:
            self._autoconfigure_port()

    def _autoconfigure_port(self):
        if os.name == "nt":
            self.port = "COM1"
        else:
            self.port = "/dev/ttyAMA0"


    def init_communication(self, max_retries=None, timeout=3*60, delay=60):
        starttime = datetime.now()

        while (True):

            if (starttime - datetime.now()).seconds > timeout:
                logger.error("Could not initilize within 3 minutes")        
                g_interface.reqReset()
                raise CommunicationError('Failed to initialize communication')

            if not self.model:
                g_interface.reqVersion()   # Ask interface of version
                sleep(delay)
                continue

            if not self.sensors:
            if g_startseq == START_INT_OK:   # If no H1 List read
                g_interface.reqList() # Request List
                s_io.debugprint("Requesting sensor list...",3)
                self.initTries=self.initTries+1

            if g_startseq == START_LIST_OK:   # If no H1 data in
                g_interface.reqStat() # Request refresh-data from interface    
                s_io.debugprint("Requesting sensor data dump",3)
                self.initTries=self.initTries+1

    def open


    def add_callback(callback):
        pass

    def connect(self):
        pass

    def disconnect(self):
        pass

    def write(self, data):
        pass

    def read(self):
        pass

    def step(self, count=1):
        pass

    def handle_data(self):
        pass

    def _read_raw(self, data):
        pass

    def _write_raw(self, data):
        pass

    def serial_in(indata):
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

def serial_in(indata):
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




class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

class ClientWorker(StoppableThread):

    def __init__(self, client, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = client

    def run(self):
        while not self.stopped():
            try:
                if g_interface.portstatus == 1:
                    raise RuntimeError('port closed')

                msg = g_interface.readline()  # Read data to cr/lf
                d = msg.decode("utf-8",errors='ignore') ## Decode from byte to str  (errors='replace')                
                d = str(d).strip()    ## Remove cr, lf and spaces in the beginning and end of string

                if d != "" :
                    serial_in(d)

                client.step()

            except:
                logger.exception('Could not parse serial input')
                d = ""   


