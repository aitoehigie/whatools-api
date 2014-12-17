#!/usr/bin/python
#  -*- coding: utf8 -*-

import json, base64, time, httplib, urllib
from bottle import route, run, request, static_file, BaseRequest
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

BaseRequest.MEMFILE_MAX = 1.5 * 1024 * 1024 

running = {}
uploads = {}

client = MongoClient('localhost')
db = client.waapi
db.authenticate('waapi', 'adventuretime')

Lines = db.lines
Chats = db.chats
Avatars = db.avatars

freePlanSignature = "\n\n[Message sent by using a WhaTools free account.\nIf it's SPAM, report it to https://wha.tools/report]"
storage = "/var/waapi/storage/"

def recover():
  activeLines = Lines.find({"tokens.active": True}, {"tokens.$": 1})
  for line in activeLines:
    token = line["tokens"][0]
    print "@@@ RECOVERING TOKEN {0} FOR LINE {1} @@@".format(token["key"], line["_id"])
    fullLine = Lines.find_one({"_id": line["_id"]})
    wa = WhatsappBackClient(fullLine, token, eventHandler, True, True)
    if wa:
      user = fullLine["cc"] + fullLine["pn"]
      pw = base64.b64decode(bytes(fullLine["pass"].encode('utf-8')))
      if wa.login(user, pw):
        if fullLine["_id"] in running:
          running[fullLine["_id"]]["tokens"].append(token["key"])
        else:
          running[fullLine["_id"]] = {
            "yowsup": wa,
            "tokens": [token["key"]]
          }
        print "@@@@ RECOVER SUCCESS @@@@"
      else:
        print "@@@@ RECOVER ERROR @@@@"
    else:
      print "@@@@ RECOVER ERROR @@@@"
  print "@@@@@@@@@@@@@"
  print running
  print "@@@@@@@@@@@@@"

def lineIsNotExpired(line):
  now = long(time.time()*1000)
  return now < line["expires"]
  
def messageSign(text, line):
  if line["plan"] == "free":
    text += freePlanSignature
  return text

def push(token, method, data):
  res = False
  url = token["push"]
  data["_method"] = method
  data["_tokenId"] = token["id"]
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
    message = Chats.find_one({"from": wa.line["_id"], "to": jid.split("@")[0], 'messages.id': messageId}, {"messages.$": 1})["messages"][0]
    if "ack" in message and message["ack"] == "delivered":
      grade = "visible"
    for token in allTokens:
      if token["key"] in runningTokens:
        if token["push"]:
          res = push(token, "ack", {"grade": grade, "jid": jid, "messageId": messageId})
          if res:
            print res.read()
    Chats.update({"from": wa.line["_id"], "to": jid.split("@")[0], 'messages.id': messageId}, {"$set": {'messages.$.ack': grade}})

def onAuthFailed(wa):
  Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": False, "reconnect": False, "valid": False}});

def onAuthSuccess(wa):
  Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": True, "reconnect": True, "valid": True}});
  wa.errors = 0

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
    
def onMediaReceived(wa, messageId, jid, caption, type, preview, url, size, wantsReceipt, isBroadCast):
  if len(running):
    allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens:
        if token["push"]:
          if type == "location":
            res = push(token, "media", {"messageId": messageId, "jid": jid, "type": type, "preview": preview, "latitude": url, "longitude": size, "wantsReceipt": wantsReceipt, "isBroadCast": isBroadCast})
          else:
            res = push(token, "media", {"messageId": messageId, "jid": jid, "type": type, "preview": preview, "url": url, "size": size, "wantsReceipt": wantsReceipt, "isBroadCast": isBroadCast})
          if res:
            print res.read()
  to = jid.split("@")[0]
  chat = Chats.find_one({"from": wa.line["_id"], "to": to})
  stamp = long(time.time())*1000
  msg = {
    "id": messageId,
    "mine": False,
    "stamp": stamp,
    "media": {
      "type": type,
      "preview": preview,
      "latitude": url,
      "longitude": size
    } if type == "location" else {
      "type": type,
      "preview": preview,
      "url": url,
      "size": size
    }
  }
  if caption:
    msg["body"] = caption;
  if chat:
    # Push it to db
    Chats.update({"from": wa.line["_id"], "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp}, "$inc": {"unread": 1}});
  else:
    # Create new chat
    Chats.insert({
      "_id": str(objectid.ObjectId()),
      "from": wa.line["_id"],
      "to": to,
      "messages": [msg],
      "lastStamp": stamp,
      "alias": pushName or False
    })

def onMessageReceived(wa, messageId, jid, messageContent, timestamp, wantsReceipt, pushName, isBroadCast):
  if len(running):
    allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens:
        if token["push"]:
          res = push(token, "message", {"messageId": messageId, "jid": jid, "messageContent": messageContent, "timestamp": timestamp, "wantsReceipt": wantsReceipt, "pushName": pushName, "isBroadCast": isBroadCast})
          if res:
            print res.read()
  to = jid.split("@")[0]
  chat = Chats.find_one({"from": wa.line["_id"], "to": to})
  stamp = long(timestamp)*1000
  msg = {
    "id": messageId,
    "mine": False,
    "body": messageContent,
    "stamp": stamp
  }
  if chat:
    # Push it to db
    Chats.update({"from": wa.line["_id"], "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp}, "$inc": {"unread": 1}});
  else:
    # Create new chat
    Chats.insert({
      "_id": str(objectid.ObjectId()),
      "from": wa.line["_id"],
      "to": to,
      "messages": [msg],
      "lastStamp": stamp,
      "alias": pushName or False
    })
  
def onPing(wa, pingId):
  line = wa.line
  if (not lineIsNotExpired(line)):
    Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False, "active": False}})
    wa = running[line["_id"]]["yowsup"]
    wa.logout()
    # TODO: Notify expiracy to active tokens
    del running[line["_id"]]
  
def onProfileSetPictureError(wa, idx, errorCode):
  if idx in uploads:
    allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens and token["key"] == uploads[idx]["token"] and token["push"]:
        res = push(token, "error", {"type": "onProfileSetPictureError", "idx": idx})
    del uploads[idx]

def onProfileSetPictureSuccess(wa, idx, pictureId):
  if idx in uploads:
    line = wa.line
    src = uploads[idx]["src"]
    item = {
      "src": src,
      "id": pictureId
    }
    Avatars.update({"jid": line["cc"] + line["pn"]}, {"$push": {"items": item}}, True)
    allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens and token["key"] == uploads[idx]["token"] and token["push"]:
          res = push(token, "success", {"type": "onProfileSetPictureSuccess", "idx": idx, "pictureId": pictureId})
    del uploads[idx]

def onProfileSetStatusSuccess(wa, jid, idx):
  allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
  runningTokens = running[wa.line["_id"]]["tokens"]
  for token in allTokens:
    if token["key"] in runningTokens and token["push"]:
        res = push(token, "success", {"type": "onProfileSetStatusSuccess", "idx": idx})


eventHandler = {
  "onAck": onAck,
  "onAuthFailed": onAuthFailed,
  "onAuthSuccess": onAuthSuccess,
  "onDisconnected": onDisconnected,
  "onMediaReceived": onMediaReceived,
  "onMessageReceived": onMessageReceived,
  "onPing": onPing,
  "onProfileSetPictureError": onProfileSetPictureError,
  "onProfileSetPictureSuccess": onProfileSetPictureSuccess,
  "onProfileSetStatusSuccess": onProfileSetStatusSuccess
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
                stamp = long(time.time()*1000)
                msg = {
                  "id": msgId,
                  "mine": True,
                  "body": body,
                  "stamp": stamp,
                  "ack": "sent"
                }
                if chat:
                  # Push it
                  Chats.update({"from": me, "to": to}, {"$push": {"messages": msg}, "$set": {"unread": 0}});
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
                      pushRes = push(token, "carbon", {"messageId": msgId, "jid": to, "messageContent": body, "timestamp": stamp, "wantsReceipt": ack, "isBroadCast": broadcast})
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
            Lines.update({"_id": lId, "tokens.key": token["key"]}, {"$set": {"valid": True, "active": True, "tokens.$.active": True}})
            res["success"] = True
          else:
            wa = WhatsappBackClient(line, token, eventHandler, True, True)
            if wa:
              user = line["cc"] + line["pn"]
              try:
                pw = base64.b64decode(bytes(line["pass"].encode('utf-8')))
              except TypeError:
                res["error"] = "password-type-error"
                Lines.update({"_id": lId, "tokens.key": token["key"]}, {"$set": {"valid": "wrong", "reconnect": False, "tokens.$.active": False}})
                return res
              running[lId] = {
                "yowsup": wa,
                "tokens": [token["key"]]
              }
              loginRes = wa.login(user, pw)
              if (loginRes == "success"):
                res["success"] = True
                if line["nickname"]:
                  wa.presence_sendAvailableForChat(line["nickname"])
                Lines.update({"_id": lId, "tokens.key": token["key"]}, {"$set": {"valid": True, "active": True, "tokens.$.active": True}})
              else:
                del running[lId]
                res["error"] = "auth-failed"
                Lines.update({"_id": lId, "tokens.key": token["key"]}, {"$set": {"valid": "wrong", "reconnect": False, "tokens.$.active": False}})
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
        if lId in running and token["key"] in running[lId]["tokens"]:
          Lines.update({"_id": lId, "tokens.key": token["key"]}, {"$set": {"tokens.$.active": False}})
          wa = running[lId]["yowsup"]
          wa.logout()
          if token["key"] in running[lId]["tokens"]:
            running[lId]["tokens"].remove(token["key"])
          if len(running[lId]["tokens"]) < 1:
            Lines.update({"_id": lId}, {"$set": {"reconnect": False, "active": False}})
            if lId in running:
              del running[lId]
          res["success"] = True
        else:
          res["error"] = "token-was-not-subscribed"
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


@route("/history", method="GET")
def history():
  res = {"success": False}
  key = request.params.key
  start = request.params.start or long(0)
  end = request.params.end or long(time.time()*1000)
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if token:
        if "permissions" in token and "manage" in token["permissions"]:
          obj = {
            "messages": [],
            "totals": {
              "all": 0,
              "in": 0,
              "out": 0
            }
          }
          myChats = Chats.find({"from": lId})
          for chat in myChats:
            for message in chat["messages"]:
              if long(message["stamp"]) >= long(start) and long(message["stamp"]) <= long(end):
                message["from"] = line["cc"] + line["pn"]
                message["to"] = chat["to"]
                obj["messages"].append(message)
                if message["mine"] == True:
                  obj["totals"]["out"] += 1
                else:
                  obj["totals"]["in"] += 1
          obj["totals"]["all"] = len(obj["messages"])
          res["result"] = json.dumps(obj)
          res["success"] = True
        else:
          res["error"] = "no-permission"
      else:
        res["error"] = "no-token-matches-key"
    else:
      res["error"] = "no-line-matches-key"
  else:
    res["error"] = "no-key"
  return res
  
@route("/nickname", method="GET")
def nickname_get():
  res = {"success": False}
  key = request.params.key
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if token:
        if "permissions" in token and "read" in token["permissions"]:
          res["result"] = line["nickname"] if "nickname" in line else False
          res["success"] = True
        else:
          res["error"] = "no-permission"
      else:
        res["error"] = "no-token-matches-key"
    else:
      res["error"] = "no-line-matches-key"
  else:
    res["error"] = "no-key"
  return res

@route("/nickname", method="POST")
def nickname_post():
  res = {"success": False}
  key = request.params.key
  nickname = request.params.nickname
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if lineIsNotExpired(line):
        if token:
          if "permissions" in token and "manage" in token["permissions"]:
            if nickname:
              if line["_id"] in running:
                wa = running[line["_id"]]["yowsup"]
                wa.presence_sendAvailableForChat(nickname)
                Lines.update({"_id": lId}, {"$set": {"nickname": nickname}})
                res["success"] = True
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
  
@route("/status", method="POST")
def status_post():
  res = {"success": False}
  key = request.params.key
  message = request.params.message
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if lineIsNotExpired(line):
        if token:
          if "permissions" in token and "manage" in token["permissions"]:
            if message:
              if line["_id"] in running:
                wa = running[line["_id"]]["yowsup"]
                wa.profile_setStatus(message.encode('utf-8').strip())
                Lines.update({"_id": lId}, {"$set": {"statusMessage": message}})
                res["success"] = True
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

@route("/avatar", method="POST")
def nickname_post():
  res = {"success": False}
  key = request.params.key
  src = request.params.src
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if lineIsNotExpired(line):
        if token:
          if "permissions" in token and "manage" in token["permissions"]:
            if src:
              if line["_id"] in running:
                wa = running[line["_id"]]["yowsup"]
                name = "avatars/" + line["cc"] + line["pn"] + "-" + str(int(time.time())) + ".jpg"
                path = storage + name
                f = open(path, "wb")
                f.write(src.decode('base64'))
                f.close()
                idx = wa.profile_setPicture(path)
                if idx:
                  uploads[idx] = {
                    "src": name,
                    "token": token["key"]
                  }
                  res["success"] = True
                else:
                  res["error"] = "wrong-file-type"
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
  
'''

STATIC CONTENT

'''

@route("/reference", method="GET")
def reference():
  return static_file('reference.htm', './static')

recover()
run(host="127.0.0.1", port="8080", server='paste')
