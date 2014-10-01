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
import time

from Yowsup.connectionmanager import YowsupConnectionManager

class WhatsappTestClient:
  
  def __init__(self):
    
    connectionManager = YowsupConnectionManager()
    self.signalsInterface = connectionManager.getSignalsInterface()
    self.methodsInterface = connectionManager.getMethodsInterface()
    
    self.signalsInterface.registerListener("auth_success", self.onAuthSuccess)
    self.signalsInterface.registerListener("auth_fail", self.onAuthFailed)
    self.signalsInterface.registerListener("disconnected", self.onDisconnected)

    self.result = False
    self.done = False
  
  def login(self, username, password):
    self.username = username
    self.methodsInterface.call("auth_login", (username, password))

    while not self.done:
      time.sleep(0.5)
      
    return self.result

  def onAuthSuccess(self, username):
    print("Authed %s" % username)
    self.result = "valid"
    self.done = True

  def onAuthFailed(self, username, err):
    print("Auth Failed!")
    self.result = "invalid"
    self.done = True

  def onDisconnected(self, reason):
    print("Disconnected because %s" %reason)

  def onMessageSent(self, jid, messageId):
    self.gotReceipt = True
