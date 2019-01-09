class Handler:

    def __init__():
        pass


import sys, os, threading, serial, atexit, datetime, urllib, urllib2, time, struct,s_io
import paho.mqtt.client as mqtt

MQTT_ENABLED = 1
MQTT_BROKER_ADDR = "srv
MQTT_BROKER_PORT = 1883


class MqttHandler(Handler):   
    
    def init(self):
       s_io.debugprint ("Mqtt Enabled = "+str(MQTT_ENABLED),2)
       if MQTT_ENABLED != 1: return
       self.mqtt_client = mqtt.Client()
       self.mqtt_client.on_connect = self.on_connect
       self.mqtt_client.on_disconnect = self.on_disconnect
       self.mqtt_client.on_message = self.on_message
	   
    # Connect to broker
    def connect(self):
       if MQTT_ENABLED != 1: return
       s_io.debugprint ("Mqtt connect:"+MQTT_BROKER_ADDR,3)
       try:
          self.mqtt_client.connect(MQTT_BROKER_ADDR, MQTT_BROKER_PORT, 60)
          self.mqtt_status=1
       except:	
          s_io.debugprint ("Cannot connect to Mqtt broker on address and port: " + MQTT_BROKER_ADDR + ":" + str(MQTT_BROKER_PORT) ,1)
          self.mqtt_status=0
	
    # PUBLISH message to broker
    def publish(self, sensor, data):
          if MQTT_ENABLED != 1: return
          #s_io.debugprint ("heatpump/"+sensor + " MQ " + str(data),3)
          if self.mqtt_status!=0: self.mqtt_client.publish("heatpump/"+sensor, payload=+data, qos=0, retain=False)
	
    # The MQTT callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
       print("Mqtt-Connect code: "+str(rc))
       # Subscribing in on_connect() means that if we lose the connection and
       # reconnect then subscriptions will be renewed.
       # client.subscribe("$SYS/#")
	   
    def on_disconnect(self, client, userdata, rc):
	   s_io.debugprint("Mqtt lost connection with broker",2)
	   self.mqtt_status=5 # Disconnected, retry every min.

    # The MQTT callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
       print("Mqtt-Rcv: "+msg.topic+" "+str(msg.payload))

    # Reconnect every 3 min
    def reconnect(self):
       if MQTT_ENABLED != 1: return
       if self.mqtt_status == 5: 
           s_io.debugprint("Mqtt Reconnecting",2)
           self.mqtt_client.reconnect()            
