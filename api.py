import json, base64
import time
from bottle import route, run, request
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

client = MongoClient('mongodb://192.168.1.2')
db = client.waapi

Users = db.users
Lines = db.lines
Chats = db.chats

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

def onMessageReceived(line, messageId, jid, messageContent, timestamp, wantsReceipt, pushName, isBroadCast):
  to = jid.split("@")[0]
  chat = Chats.find_one({"from": line["_id"], "to": to})
  stamp = int(timestamp)*1000
  msg = {
    "mine": False,
    "body": messageContent,
    "stamp": stamp
  }
  if chat:
    # Push it
    Chats.update({"from": line["_id"], "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp}});
  else:
    # Create new chat
    Chats.insert({
      "_id": str(objectid.ObjectId()),
      "from": line,
      "to": to,
      "messages": [msg],
      "lastStamp": stamp
    })

eventHandler = {
  "onAuthFailed": onAuthFailed,
  "onAuthSuccess": onAuthSuccess,
  "onDisconnected": onDisconnected,
  "onMessageReceived": onMessageReceived
}

running = {}

@route("/message", method="POST")
def messages_post():
  res = {"success": False}
  key = request.params.key
  to = request.params.to
  body = request.params.body.encode('utf8','replace')
  ack = request.params.ack
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      me = line["_id"]
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if token:
        if "permissions" in token and "write" in token["permissions"]:
          if to and body:
            if line["_id"] in running:
              wa = running[line["_id"]]["yowsup"];
              wa.say(to, body, ack)
              res["success"] = True
              chat = Chats.find_one({"from": me, "to": to})
              stamp = int(time.time()*1000)
              msg = {
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
            else:
              res["error"] = "inactive-line"
          else:
            res["error"] = "bad-param"
        else:
          res["error"] = "no-permission"
      else:
        res["error"] = "no-token"
    else:
      res["error"] = "invalid-key"
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
  
@route("/line/activate", method="GET")
def line_activate():
  res = {"success": False}
  key = request.params.key
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
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
          wa = WhatsappBackClient(line, eventHandler, True, True)
          if wa:
            user = line["cc"] + line["pn"]
            try:
              pw = base64.b64decode(bytes(line["pass"].encode('utf-8')))
            except TypeError:
              res["error"] = "password-type-error"
              Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False}})
              return res
            loginRes = wa.login(user, pw)
            if (loginRes == "success"):
              res["success"] = True
              running[lId] = {
                "yowsup": wa,
                "tokens": [token["key"]]
              }
              Lines.update({"_id": lId}, {"$set": {"valid": True, "active": True}})
            else:
              res["error"] = "auth-failed"
              Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False}})
          else:
            res["error"] = "could-not-connect"
      else:
        res["error"] = "no-token"
    else:
      res["error"] = "invalid-key"
  else:
    res["error"] = "no-key"
  print ">>>>>>>>>>>>>"
  print running
  print ">>>>>>>>>>>>>"
  return res
  
@route("/line/deactivate", method="GET")
def line_activate():
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
          res["error"] = "no-such-line"
      else:
        res["error"] = "no-token"
    else:
      res["error"] = "invalid-key"
  else:
    res["error"] = "no-key"
  print "<<<<<<<<<<<<<"
  print running
  print "<<<<<<<<<<<<<"
  return res

run(host="192.168.2.2", port="8080", debug=True, reloader=True)
