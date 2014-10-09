'''
Copyright (c) <2012> Tarek Galal <tare2.galal@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)
import time, datetime, sys

if sys.version_info >= (3, 0):
  raw_input = input

from Yowsup.connectionmanager import YowsupConnectionManager

class WhatsappBackClient:
  
  def __init__(self, line, eventHandler, keepAlive = True, sendReceipts = False):
    self.line = line
    self.eventHandler = eventHandler
    self.sendReceipts = sendReceipts
    connectionManager = YowsupConnectionManager()
    connectionManager.setAutoPong(keepAlive)
    self.signalsInterface = connectionManager.getSignalsInterface()
    self.methodsInterface = connectionManager.getMethodsInterface()
    self.signalsInterface.registerListener("message_received", self.onMessageReceived)
    self.signalsInterface.registerListener("auth_success", self.onAuthSuccess)
    self.signalsInterface.registerListener("auth_fail", self.onAuthFailed)
    self.signalsInterface.registerListener("disconnected", self.onDisconnected)
    self.cm = connectionManager
    self.result = False
    self.done = False
    self.username = False
    self.password = False
    self.errors = 0
  
  def login(self, username, password):
    self.username = username
    self.password = password
    self.methodsInterface.call("auth_login", (username, password))
    while not self.done:
      time.sleep(0.2)
    return self.result
    
  def logout(self):
    self.methodsInterface.call("disconnect")
  
  def onAuthSuccess(self, username):
    print("Authed %s" % username)
    self.methodsInterface.call("ready")
    self.result = "success"
    self.done = True
    self.eventHandler["onAuthSuccess"](self)

  def onAuthFailed(self, username, err):
    print("Auth Failed!")
    self.result = "failed"
    self.done = True
    self.eventHandler["onAuthFailed"](self)

  def onDisconnected(self, reason):
    self.eventHandler["onDisconnected"](self, reason)
    print("Disconnected because %s" %reason)

  def onMessageReceived(self, messageId, jid, messageContent, timestamp, wantsReceipt, pushName, isBroadCast):
    formattedDate = datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')
    self.eventHandler["onMessageReceived"](self, messageId, jid, messageContent, timestamp, wantsReceipt, pushName, isBroadCast)
    print("%s [%s]:%s"%(jid, formattedDate, messageContent))
    if wantsReceipt and self.sendReceipts:
      self.methodsInterface.call("message_ack", (jid, messageId))
      
  def say(self, to, body, ack = False):
    self.methodsInterface.call("message_send", (to + "@s.whatsapp.net", body))
    return True
  
