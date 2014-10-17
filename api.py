#!/usr/bin/python
#  -*- coding: utf8 -*-

import json, base64, time, httplib, urllib
from bottle import route, run, request, static_file
from pymongo import MongoClient
from bson import objectid
from Yowsup.Common.utilities import Utilities
from Yowsup.Common.debugger import Debugger
from Yowsup.Common.constants import Constants
from Clients.TestClient import WhatsappTestClient
from Clients.SimpleClient import WhatsappSimpleClient
from Clients.BackClient import WhatsappBackClient
from Yowsup.Contacts.contacts import WAContactsSyncRequest
from Yowsup.Registration.v2.coderequest import WACodeRequest
from Yowsup.Registration.v2.existsrequest import WAExistsRequest
from Yowsup.Registration.v2.regrequest import WARegRequest

running = {}

client = MongoClient('mongodb://127.0.0.1')
db = client.waapi
db.authenticate('waapi', 'adventuretime')

Users = db.users
Lines = db.lines
Chats = db.chats

freePlanSignature = "\n\n[Message sent by using WAAPI. If it's SPAM, report it to https://waapi.com/report]"

def lineIsNotExpired(line):
  now = int(time.time()*1000)
  return now < line["expires"]
  
def messageSign(text, line):
  if line["plan"] == "free":
    text += freePlanSignature
  return text

def push(url, method, data):
  res = False
  data["_method"] = method
  params = urllib.urlencode(data)
  headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
  if url[0] == "https":
    conn = httplib.HTTPSConnection(url[1], int(url[2]))
  else:
    conn = httplib.HTTPConnection(url[1], int(url[2]))
  try:
    conn.request("POST", '/' + url[3], params, headers)
    res = conn.getresponse()
  except:
    print "[PUSH] Connection refused while trying to " + method
  return res

def onAck(wa, grade, jid, messageId):
  print "ACK from " + jid + " to " + wa.line["cc"] + wa.line["pn"]
  if len(running):
    allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens:
        if token["push"]:
          res = push(token["push"], "ack", {"grade": grade, "jid": jid, "messageId": messageId})
          if res:
            print res.read()

def onAuthFailed(wa):
  Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": False, "reconnect": False, "valid": False}});

def onAuthSuccess(wa):
  Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": True, "reconnect": True, "valid": True}});

def onDisconnected(wa, reason):
  line = Lines.find_one({"_id": wa.line["_id"]});
  if wa.errors < 3:
    Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": False}});
    wa.errors += 1
    if line["reconnect"]:
      wa.login(wa.username, wa.password);
  else:
    Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": False, "reconnect": False}});
    wa.errors = 0

def onMessageReceived(wa, messageId, jid, messageContent, timestamp, wantsReceipt, pushName, isBroadCast):
  if len(running):
    allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens:
        if token["push"]:
          res = push(token["push"], "message", {"messageId": messageId, "jid": jid, "messageContent": messageContent, "timestamp": timestamp, "wantsReceipt": wantsReceipt, "pushName": pushName, "isBroadCast": isBroadCast})
          if res:
            print res.read()
  to = jid.split("@")[0]
  chat = Chats.find_one({"from": wa.line["_id"], "to": to})
  stamp = int(timestamp)*1000
  msg = {
    "id": messageId,
    "mine": False,
    "body": messageContent,
    "stamp": stamp
  }
  if chat:
    # Push it to db
    Chats.update({"from": wa.line["_id"], "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp}});
  else:
    # Create new chat
    Chats.insert({
      "_id": str(objectid.ObjectId()),
      "from": wa.line["_id"],
      "to": to,
      "messages": [msg],
      "lastStamp": stamp
    })
  
def onPing(wa, pingId):
  line = wa.line
  if (not lineIsNotExpired(line)):
    Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False, "active": False}})
    wa = running[line["_id"]]["yowsup"]
    wa.logout()
    # TODO: Notify expiracy to active tokens
    del running[line["_id"]]
  
eventHandler = {
  "onAck": onAck,
  "onAuthFailed": onAuthFailed,
  "onAuthSuccess": onAuthSuccess,
  "onDisconnected": onDisconnected,
  "onMessageReceived": onMessageReceived,
  "onPing": onPing
}

@route("/message", method="POST")
def messages_post():
  res = {"success": False}
  key = request.params.key
  to = request.params.to
  body = request.params.body.encode('utf8','replace')
  ack = request.params.ack
  broadcast = request.params.broadcast
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      me = line["_id"]
      if lineIsNotExpired(line):
        token = filter(lambda e: e['key'] == key, line['tokens'])[0]
        if token:
          if "permissions" in token and "write" in token["permissions"]:
            if to and body:
              if line["_id"] in running:
                signedBody = messageSign(body, line)
                wa = running[line["_id"]]["yowsup"]
                msgId = wa.say(to, signedBody, ack)
                res["result"] = msgId
                res["success"] = True
                chat = Chats.find_one({"from": me, "to": to})
                stamp = int(time.time()*1000)
                msg = {
                  "id": msgId,
                  "mine": True,
                  "body": body,
                  "stamp": stamp
                }
                if chat:
                  # Push it
                  Chats.update({"from": me, "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp}});
                else:
                  # Create new chat
                  Chats.insert({
                    "_id": str(objectid.ObjectId()),
                    "from": me,
                    "to": to,
                    "messages": [msg],
                    "lastStamp": stamp
                  })
                runningTokens = running[line["_id"]]["tokens"]
                for token in line["tokens"]:
                  if token["key"] in runningTokens:
                    if token["push"] and token["key"] != key:
                      pushRes = push(token["push"], "carbon", {"messageId": msgId, "jid": to, "messageContent": body, "timestamp": stamp, "wantsReceipt": ack, "isBroadCast": broadcast})
                      if pushRes:
                        print pushRes.read()
              else:
                res["error"] = "inactive-line"
            else:
              res["error"] = "bad-param"
          else:
            res["error"] = "no-permission"
        else:
          res["error"] = "no-token-matches-key"
      else:
        res["error"] = "line-is-expired"
        Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False, "active": False}})
    else:
      res["error"] = "no-line-matches-key"
  else:
    res["error"] = "no-key"
  return res

@route("/line/coderequest", method="GET")
def line_validate():
  res = {"success": False}
  pn = request.params.pn
  cc = request.params.cc
  method = request.params.method
  if pn and cc:
    wa = WACodeRequest(cc, pn, Utilities.processIdentity(""), method)
    if wa:
      res["success"] = True
      res["result"] = wa.send()
    else:
      res["error"] = "could-not-send"
  else:
    res["error"] = "bad-param"
  return res

@route("/line/regrequest", method="GET")
def line_validate():
  res = {"success": False}
  pn = request.params.pn
  cc = request.params.cc
  code = request.params.code
  if pn and cc and code:
    wa = WARegRequest(cc, pn, code, Utilities.processIdentity(""))
    if wa:
      res["success"] = True
      res["result"] = wa.register()
    else:
      res["error"] = "could-not-register"
  else:
    res["error"] = "bad-param"
  return res
  
@route("/line/test", method="GET")
def line_validate():
  res = {"success": False}
  lId = request.params.id
  if lId:
    line = Lines.find_one({"_id": lId})
    if line:
      wa = WhatsappTestClient()
      if wa:
        user = line["cc"] + line["pn"]
        try:
          pw = base64.b64decode(bytes(line["pass"].encode('utf-8')))
        except TypeError:
          res["error"] = "password-type-error"
          Lines.update({"_id": lId}, {"$set": {"valid": "wrong"}})
          return res
        res["success"] = True
        res["result"] = wa.login(user, pw)
        if (res["result"] == "valid"):
          Lines.update({"_id": lId}, {"$set": {"valid": True}})
        else:
          Lines.update({"_id": lId}, {"$set": {"valid": "wrong"}})
      else:
        res["error"] = "could-not-connect"
    else:
      res["error"] = "no-such-line"
  else:
    res["error"] = "bad-param"
  return res
  
@route("/subscribe", method="GET")
def line_subscribe():
  res = {"success": False}
  key = request.params.key
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
      if lineIsNotExpired(line):
        token = filter(lambda e: e['key'] == key, line['tokens'])[0]
        if token:
          if lId in running:
            wa = running[lId]["yowsup"]
            # TODO: Check if connected and reconnect if not
            if token["key"] not in running[lId]["tokens"]:
              running[lId]["tokens"].append(token["key"])
            Lines.update({"_id": lId}, {"$set": {"valid": True, "active": True}})
            res["success"] = True
          else:
            wa = WhatsappBackClient(line, token, eventHandler, True, True)
            if wa:
              user = line["cc"] + line["pn"]
              try:
                pw = base64.b64decode(bytes(line["pass"].encode('utf-8')))
              except TypeError:
                res["error"] = "password-type-error"
                Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False}})
                return res
              running[lId] = {
                "yowsup": wa,
                "tokens": [token["key"]]
              }
              loginRes = wa.login(user, pw)
              if (loginRes == "success"):
                res["success"] = True
                Lines.update({"_id": lId}, {"$set": {"valid": True, "active": True}})
              else:
                del running[lId]
                res["error"] = "auth-failed"
                Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False}})
            else:
              res["error"] = "could-not-connect"
        else:
          res["error"] = "no-token-matches-key"
      else:
        res["error"] = "line-is-expired"
        Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False, "active": False}})
    else:
      res["error"] = "no-line-matches-key"
  else:
    res["error"] = "no-key"
  print ">>>>>>>>>>>>>"
  print running
  print ">>>>>>>>>>>>>"
  return res
  
@route("/unsubscribe", method="GET")
def line_unsubscribe():
  res = {"success": False}
  key = request.params.key
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if token:
        if lId in running:
          Lines.update({"_id": lId}, {"$set": {"reconnect": False, "active": False}})
          wa = running[lId]["yowsup"]
          wa.logout()
          running[lId]["tokens"].remove(token["key"])
          if len(running[lId]["tokens"]) < 1:
            del running[lId]
          res["success"] = True
        else:
          res["error"] = "line-was-not-running"
      else:
        res["error"] = "no-token-matches-key"
    else:
      res["error"] = "no-line-matches-key"
  else:
    res["error"] = "no-key"
  print "<<<<<<<<<<<<<"
  print running
  print "<<<<<<<<<<<<<"
  return res
  
  
'''

STATIC CONTENT

'''

@route("/reference", method="GET")
def reference():
  return static_file('reference.htm', './static')

run(host="192.168.2.2", port="8080", server='paste')
