#!/usr/bin/python
#  -*- coding: utf8 -*-

import sys, json, base64, time, httplib, urllib, gevent, phonenumbers
from gevent import Greenlet, queue, monkey; monkey.patch_all()
from bottle import route, run, request, response, static_file, BaseRequest, FormsDict
from pymongo import MongoClient
from bson import objectid
from client.stack import YowsupAsyncStack
from yowsup.registration import *
from yowsup.layers import *
from lxml import etree
from PIL import Image
import Bot

reload(sys)
sys.setdefaultencoding('utf8')

BaseRequest.MEMFILE_MAX = 1.5 * 1024 * 1024 

running = {}
uploads = {}

client = MongoClient('localhost')
db = client.waapi
db.authenticate('waapi', 'adventuretime')

Lines = db.lines
Chats = db.chats
Avatars = db.avatars
Logs = db.logs

v = "1"
freePlanSignature = "\n\n[Message sent from a WhaTools free account.\nIf SPAM, please report to https://wha.tools/report]"
storage = "/var/waapi/storage/"


def logger(lId, event, data={}):
  if lId and event:
    Logs.insert({"line": lId, "stamp": long(time.time())*1000, "event": event, "data": data})

def unbottle(data):
  dataDict = {}
  for item in data:
    dataDict[item] = data[item]
  return dataDict
  
def phoneFormat(cc, pn):
  region = phonenumbers.region_code_for_country_code(int(cc))
  parsed = phonenumbers.parse(pn, region)
  formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
  clean = formatted.replace("+", "")
  return clean
  
def botify(wa, msg, pn):
  def action_answer(msg, payload):
    to = msg["from"]
    body = payload.encode('utf8','replace')
    stamp = long(time.time()*1000)
    chat = Chats.find_one({"from": wa.line["_id"], "to": to})
    msgId = wa.call("message_send", (msg["from"], messageSign(body, wa.line)))
    msg = {
      "id": msgId,
      "mine": True,
      "body": body,
      "stamp": stamp,
      "ack": "sent"
    }
    Chats.update({"from": wa.line["_id"], "to": to}, {"$push": {"messages": msg}});
    
  def action_canned(msg, payload):
    to = msg["from"]
    canned = next((x for x in wa.line["canned"] if x["id"] == payload), "")
    if canned and len(canned):
      body = canned["body"].encode('utf8','replace')
      stamp = long(time.time()*1000)
      chat = Chats.find_one({"from": wa.line["_id"], "to": to})
      msgId = wa.call("message_send", (msg["from"], messageSign(body, line)))
      msg = {
        "id": msgId,
        "mine": True,
        "body": body,
        "stamp": stamp,
        "ack": "sent"
      }
      Chats.update({"from": wa.line["_id"], "to": to}, {"$push": {"messages": msg}});
    
  actions = {
    'answer': action_answer,
    'canned': action_canned
  }
  line = Lines.find_one({"_id": wa.line["_id"]})
  chat = Chats.find_one({"from": wa.line["_id"],  "to": pn})
  msg["from"] = msg["participant"].split("@")[0] if "participant" in msg else pn
  region = phonenumbers.region_code_for_country_code(int(wa.line["cc"]))
  parsed = phonenumbers.parse(msg["from"], region)
  msg["cc"] = str(parsed.country_code)
  msg["pn"] = str(parsed.national_number)
  gmtime = time.gmtime(msg["stamp"]/1000)
  msg["mday"] = gmtime[2]
  msg["hour"] = gmtime[3]
  msg["wday"] = gmtime[6]
  msg["chatStatus"] =  (("archived" if ("archived" in chat and chat["archived"]) else "open") if len(chat["messages"]) > 1 else "new") if chat else "new"
  if "bots" in line:
    for bot in line["bots"]:
      if (bot["enabled"]):
        Bot.run(msg, bot["cond"], bot["cons"], actions)
        logger(line["_id"], "botProcess", msg)
 
def recover(lines=False):
  if lines:
    for line in lines:
      done = [False]
      count = 0
      res = {"success": False}
      token = line["tokens"][0]
      fullLine = Lines.find_one({"_id": line["_id"]})
      user = fullLine["cc"] + fullLine["pn"]
      logger(line["_id"], "lineRecover", [token]);
      print "@@@ RECOVERING TOKEN {0} FOR LINE {1} @@@".format(token["key"], line["_id"])
      def cb(wa, loginRes, payload):
          if loginRes == "success":
            if fullLine["_id"] in running:
              running[fullLine["_id"]]["tokens"].append(token["key"])
            else:
              running[fullLine["_id"]] = {
                "yowsup": wa,
                "tokens": [token["key"]]
              }
            print "@@@@ RECOVER SUCCESS @@@@ {0} {1}".format(token["key"], line["_id"])
            res["success"] = True
          else:
            print "@@@@ RECOVER ERROR @@@@ {0} {1}".format(token["key"], line["_id"])
            res["error"] = "auth-error"
          logger(fullLine["_id"], "lineRecoverProgress", {"res": res});
          done[0] = True
      wa = YowsupAsyncStack([user, fullLine["pass"]], fullLine, token, eventHandler, logger, cb)
      if wa:
        Greenlet.spawn(wa.login)
      else:
        res["error"] = "connect-error"
        logger(fullLine["_id"], "lineRecoverProgress", {"res": res});
        print "@@@@ RECOVER ERROR @@@@"
      while not done[0] and count < 20:
        gevent.sleep(.5)
        print count, line["_id"], done[0]
        count += 1
  return

def lineIsNotExpired(line):
  now = long(time.time()*1000)
  return now < int(line["expires"])
  
def messageSign(text, line):
  if line["plan"] == "free":
    text += freePlanSignature
  return text

def push(lId, token, method, data):
  res = False
  url = token["push"]
  data["_lineId"] = lId
  data["_tokenId"] = token["id"]
  data["_method"] = method
  params = urllib.urlencode(data)
  headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
  if url[0] == "https":
    conn = httplib.HTTPSConnection(url[1], int(url[2]))
  else:
    conn = httplib.HTTPConnection(url[1], int(url[2]))
  try:
    logger(lId, "hookPost", {"url": url, "params": params, "headers": headers})
    conn.request("POST", '/' + url[3], params, headers)
    res = conn.getresponse()
  except:
    logger(lId, "hookProgress", {"success": False, "url": url, "params": params, "headers": headers})
    print "[PUSH] Connection refused while trying to " + method
  else:  
    logger(lId, "hookProgress", {"success": True, "result": res.read(), "url": url, "params": params, "headers": headers})
  return res

def onAck(wa, idx, jid, grade):
  print "ACK from " + jid + " to " + wa.line["cc"] + wa.line["pn"] + "type: " + grade
  if len(running):
    allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    if wa.line["_id"] in running:
      runningTokens = running[wa.line["_id"]]["tokens"]
      message = Chats.find_one({"from": wa.line["_id"], "to": jid.split("@")[0], 'messages.id': idx}, {"messages.$": 1})
      if message:
        message = ["messages"][0]
        if "ack" in message and message["ack"] == "delivered":
          grade = "visible"
        for token in allTokens:
          if token["key"] in runningTokens:
            if token["push"]:
              res = push(wa.line["_id"], token, "ack", {"grade": grade, "jid": jid, "messageId": idx})
              if res:
                print res.read()
    else:
      print "WEIRD ERROR, message received for line not running"
    Chats.update({"from": wa.line["_id"], "to": jid.split("@")[0], 'messages.id': idx}, {"$set": {'messages.$.ack': grade}})
    return True

def onAuthFailed(wa):
  Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": False, "reconnect": False, "valid": False}});

def onAuthSuccess(wa):
  Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": True, "reconnect": True, "valid": True}});

def onAxolotlReady(wa):
  line = Lines.find_one({"_id": wa.line["_id"]})
  def cb(wa, loginRes, payload):
    if line["_id"] in running:
      running[line["_id"]]["yowsup"] = wa
  newWa = YowsupAsyncStack([line["cc"] + line["pn"], line["pass"]], line, line["tokens"][0], eventHandler, logger, cb)
  if newWa:
    gevent.spawn(newWa.login)

def onDisconnected(wa, reason):
  print "???? DISCONNECTION", reason, line["active"], line["reconnect"], line["_id"]
    
def onMediaReceived(wa, messageId, jid, participant, caption, type, preview, url, size, isBroadCast):
  to = jid.split("@")[0]
  chat = Chats.find_one({"from": wa.line["_id"], "to": to})
  stamp = long(time.time())*1000
  msg = {
    "id": messageId,
    "mine": False,
    "stamp": stamp,
    "media": {
      "location": {
        "type": "location",
        "preview": base64.b64encode(preview) if preview else None,
        "latitude": url,
        "longitude": size
      },
      "vcard": {
        "type": "vcard",
        "card": preview
      }
    }.get(type, {
      "type": type,
      "preview": base64.b64encode(preview) if preview else None,
      "url": url,
      "size": size
    })
  }
  if caption:
    msg["body"] = caption
  if participant:
    msg["participant"] = participant
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
      "alias": False
    })
  botify(wa, msg, to)
  if len(running):
    allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens:
        if token["push"]:
          if type == "location":
            pushData = {"messageId": messageId, "jid": jid, "type": type, "preview": preview, "latitude": url, "longitude": size, "timestamp": stamp}
          elif type == "vcard":
            url = "https://api.wha.tools/v%s/?cId=%s&mId=%s" % (v, chat["_id"], msg["id"])
            pushData = {"messageId": messageId, "jid": jid, "type": type, "name": caption, "url": url, "timestamp": stamp}
          else:
            pushData = {"messageId": messageId, "jid": jid, "type": type, "preview": preview, "url": url, "size": size, "timestamp": stamp}
          if participant:
            pushData["participant"] = participant
          if isBroadCast:
            pushData["broadcast"] = broadcast
          pushRes = push(wa.line["_id"], token, "media", pushData)
          if pushRes:
            print pushRes.read()
  return True;

def onMessageReceived(wa, messageId, jid, participant, messageContent, timestamp, pushName, isBroadCast):
  to = jid.split("@")[0]
  chat = Chats.find_one({"from": wa.line["_id"], "to": to})
  stamp = long(timestamp)*1000
  msg = {
    "id": messageId,
    "mine": False,
    "body": messageContent,
    "stamp": stamp
  }
  if participant:
    msg["participant"] = participant
    msg["pushName"] = pushName
  if isBroadCast:
    msg["broadcast"] = broadcast
  if chat:
    # Push it to db
    Chats.update({"from": wa.line["_id"], "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp}, "$inc": {"unread": 1}})
  else:
    alias = False if participant else (pushName or False)
    # Create new chat
    Chats.insert({
      "_id": str(objectid.ObjectId()),
      "from": wa.line["_id"],
      "to": to,
      "messages": [msg],
      "lastStamp": stamp,
      "alias": alias
    })
  botify(wa, msg, to)
  if len(running):
    allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    if wa.line["_id"] in running:
      runningTokens = running[wa.line["_id"]]["tokens"]
      for token in allTokens:
        if token["key"] in runningTokens:
          if token["push"]:
            pushData = {"messageId": messageId, "jid": jid, "messageContent": messageContent, "timestamp": timestamp}
            if participant:
              pushData["participant"] = participant
            if isBroadCast:
              pushData["broadcast"] = broadcast
            res = push(wa.line["_id"], token, "message", pushData)
            if res:
              print res.read()
    else:
      print "WEIRD ERROR, message received for line not running"
  return True
  
def onPing(wa, pingId):
  line = wa.line
  if (not lineIsNotExpired(line)):
    Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False, "active": False}})
    wa = running[line["_id"]]["yowsup"]
    wa.logout()
    # TODO: Notify expiracy to active tokens
    del running[line["_id"]]
  else:
    logger(line["_id"], "onPing", [pingId])
  
def onProfileSetPictureError(wa, idx, errorCode):
  if idx in uploads:
    allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens and token["key"] == uploads[idx]["token"] and token["push"]:
        res = push(wa.line["_id"], token, "error", {"type": "onProfileSetPictureError", "idx": idx})
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
          res = push(wa.line["_id"], token, "success", {"type": "onProfileSetPictureSuccess", "idx": idx, "pictureId": pictureId})
    del uploads[idx]
  else:
    print "COULD NOT RECOVER idx %s" % idx
    print uploads

def onProfileSetStatusSuccess(wa, jid, idx):
  allTokens = Lines.find_one({"_id": wa.line["_id"]})["tokens"]
  runningTokens = running[wa.line["_id"]]["tokens"]
  for token in allTokens:
    if token["key"] in runningTokens and token["push"]:
        res = push(wa.line["_id"], token, "success", {"type": "onProfileSetStatusSuccess", "idx": idx})

eventHandler = {
  "onAck": onAck,
  "onAuthFailed": onAuthFailed,
  "onAuthSuccess": onAuthSuccess,
  "onAxolotlReady": onAxolotlReady,
  "onDisconnected": onDisconnected,
  "onMediaReceived": onMediaReceived,
  "onMessageReceived": onMessageReceived,
  "onPing": onPing,
  "onProfileSetPictureError": onProfileSetPictureError,
  "onProfileSetPictureSuccess": onProfileSetPictureSuccess,
  "onProfileSetStatusSuccess": onProfileSetStatusSuccess
}


@route("/message", method="POST")
def message_post():
  res = {"success": False}
  key = request.params.key
  to = request.params.to
  body = request.params.body.encode('utf8','replace')
  broadcast = request.params.broadcast
  honor = request.params.honor
  msgId = False
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
      logger(lId, "messagePost", unbottle(request.params))
      if lineIsNotExpired(line):
        token = filter(lambda e: e['key'] == key, line['tokens'])[0]
        if token:
          if "permissions" in token and "write" in token["permissions"]:
            if to and body:
              if line["_id"] in running:
                signedBody = messageSign(body, line)
                wa = running[line["_id"]]["yowsup"]
                if not honor:
                  to = phoneFormat(line["cc"], to)
                data = [to, signedBody]
                msgId = wa.call("message_send", data)
                if msgId:
                  res["result"] = msgId
                  res["success"] = True
                  chat = Chats.find_one({"from": lId, "to": to})
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
                    Chats.update({"from": lId, "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp, "unread": 0}});
                  else:
                    # Create new chat
                    Chats.insert({
                      "_id": str(objectid.ObjectId()),
                      "from": lId,
                      "to": to,
                      "messages": [msg],
                      "lastStamp": stamp
                    })
                  runningTokens = running[line["_id"]]["tokens"]
                  for token in line["tokens"]:
                    if token["key"] in runningTokens:
                      if token["push"] and token["key"] != key:
                        pushRes = push(lId, token, "carbon", {"messageId": msgId, "jid": to, "messageContent": body, "timestamp": stamp, "isBroadCast": broadcast})
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
      logger(lId, "messageSendProgress", {"params": unbottle(request.params), "msg": msg} if msgId else {"params": unbottle(request.params), "res": res});
    else:
      res["error"] = "no-line-matches-key"
  else:
    res["error"] = "no-key"
  return res

@route("/line/coderequest", method="GET")
def line_coderequest():
  res = {"success": False}
  pn = request.params.pn
  cc = request.params.cc
  method = request.params.method
  if pn and cc:
    wa = WACodeRequest(cc, pn, method=method)
    if wa:
      res["success"] = True
      res["result"] = wa.send()
    else:
      res["error"] = "could-not-send"
  else:
    res["error"] = "bad-param"
  return res

@route("/line/regrequest", method="GET")
def line_regrequest():
  res = {"success": False}
  pn = request.params.pn
  cc = request.params.cc
  code = request.params.code
  if pn and cc and code:
    wa = WARegRequest(cc, pn, code)
    if wa:
      res["success"] = True
      res["result"] = wa.register()
    else:
      res["error"] = "could-not-register"
  else:
    res["error"] = "bad-param"
  return res
  
@route("/line/test", method="GET")
def line_test():
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
def subscribe():
  body = queue.Queue()
  res = {"success": False}
  key = request.params.key
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      if "api" in line and line["api"] == v:
        lId = line["_id"]
        logger(lId, "tokenSubscribe", unbottle(request.params));
        if lineIsNotExpired(line):
          token = filter(lambda e: e['key'] == key, line['tokens'])[0]
          if token:
            if lId in running:
              wa = running[lId]["yowsup"]
              # TODO: Check if connected and reconnect if not
              if token["key"] not in running[lId]["tokens"]:
                running[lId]["tokens"].append(token["key"])
              Lines.update({"_id": lId, "tokens.key": token["key"]}, {"$set": {"valid": True, "active": True, "tokens.$.active": True}})
              res["result"] = line["data"]
              res["result"]["cc"] = line["cc"]
              res["result"]["pn"] = line["pn"]
              res["result"]["api_expiration"] = int(line["expires"] / 1000)
              if "props" in res["result"]:
                del res["result"]["props"]
              res["success"] = True
              logger(lId, "tokenSubscribeProgress", {"params": unbottle(request.params), "res": res})
              logger(lId, "presenceSendAvailable", {"nickname": line["nickname" if "nickname" in line else None] });
              wa.call("presence_sendAvailable", [line["nickname"] if "nickname" in line else None])
              body.put(json.dumps(res))
              body.put(StopIteration)
            else:
              user = line["cc"] + line["pn"]
              def cb(wa, loginRes, payload):
                if (loginRes == "success"):
                  res["success"] = True
                  if not payload:
                    payload = line["data"]
                  res["result"] = payload
                  res["result"]["cc"] = line["cc"]
                  res["result"]["pn"] = line["pn"]
                  res["result"]["api_expiration"] = int(line["expires"] / 1000)
                  if "props" in res["result"]:
                    del res["result"]["props"]
                  res["success"] = True
                  logger(lId, "presenceSendAvailable", {"nickname": line["nickname" if "nickname" in line else None] });
                  wa.call("presence_sendAvailable", [line["nickname"] if "nickname" in line else None])
                  Lines.update({"_id": lId, "tokens.key": token["key"]}, {"$set": {"valid": True, "active": True, "tokens.$.active": True, "data": payload}})
                else:
                  del running[lId]
                  res["error"] = "auth-failed"
                  Lines.update({"_id": lId, "tokens.key": token["key"]}, {"$set": {"valid": "wrong", "reconnect": False, "tokens.$.active": False}})
                logger(lId, "tokenSubscribeProgress", {"res": res})
                body.put(json.dumps(res))
                body.put(StopIteration)
              wa = YowsupAsyncStack([user, line["pass"]], line, token, eventHandler, logger, cb)
              if wa:
                try:
                  pw = base64.b64decode(bytes(str(line["pass"])))
                except TypeError:
                  res["error"] = "password-type-error"
                  Lines.update({"_id": lId, "tokens.key": token["key"]}, {"$set": {"valid": "wrong", "reconnect": False, "tokens.$.active": False}})
                  return res
                running[lId] = {
                  "yowsup": wa,
                  "tokens": [token["key"]]
                }
                gevent.spawn(wa.login)
              else:
                res["error"] = "could-not-connect"
          else:
            res["error"] = "no-token-matches-key"
        else:
          res["error"] = "line-is-expired"
          Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False, "active": False}})
          logger(lId, "tokenSubscribeProgress", {"params": unbottle(request.params), "res": res})
      else:
        res["error"] = "wrong-api-version"
    else:
      res["error"] = "no-line-matches-key"
  else:
    res["error"] = "no-key"
  if "error" in res:
    body.put(json.dumps(res))
    body.put(StopIteration)
  return body
  
@route("/unsubscribe", method="GET")
def unsubscribe():
  res = {"success": False}
  key = request.params.key
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
      logger(lId, "tokenUnsubscribe", unbottle(request.params));
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
      logger(lId, "tokenUnsubscribeProgress", {"params": unbottle(request.params), "res": res});
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
      logger(lId, "historyGet", unbottle(request.params));
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
      logger(lId, "historyGetProgress", {"params": unbottle(request.params), "res": res});
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
      logger(lId, "nicknameGet", unbottle(request.params));
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if token:
        if "permissions" in token and "read" in token["permissions"]:
          res["result"] = line["nickname"] if "nickname" in line else False
          res["success"] = True
        else:
          res["error"] = "no-permission"
      else:
        res["error"] = "no-token-matches-key"
      logger(lId, "nicknameGetProgress", {"params": unbottle(request.params), "res": res});
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
      logger(lId, "nicknamePost", unbottle(request.params));
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if lineIsNotExpired(line):
        if token:
          if "permissions" in token and "write" in token["permissions"]:
            if nickname:
              if line["_id"] in running:
                wa = running[line["_id"]]["yowsup"]
                wa.call("presence_sendAvailable", [nickname])
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
      logger(lId, "nicknamePostProgress", {"params": unbottle(request.params), "res": res});
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
      logger(lId, "statusPost", unbottle(request.params));
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if lineIsNotExpired(line):
        if token:
          if "permissions" in token and "write" in token["permissions"]:
            if message:
              if line["_id"] in running:
                wa = running[line["_id"]]["yowsup"]
                wa.call("profile_setStatus", [message.encode('utf-8').strip()])
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
      logger(lId, "statusPostProgress", {"params": unbottle(request.params), "res": res});
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
      logger(lId, "avatarPost", unbottle(request.params));
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if lineIsNotExpired(line):
        if token:
          if "permissions" in token and "write" in token["permissions"]:
            if src:
              if line["_id"] in running:
                wa = running[line["_id"]]["yowsup"]
                name = "avatars/" + line["cc"] + line["pn"] + "-" + str(int(time.time())) + ".jpg"
                path = storage + name
                f = open(path, "wb")
                f.write(src.decode('base64'))
                f.close()
                src = Image.open(path)
                pictureData = bytearray(src.resize((640, 640)).tostring("jpeg", "RGB"))
                previewData = bytearray(src.resize((96, 96)).tostring("jpeg", "RGB"))
                idx = wa.call("profile_setPicture", [pictureData, previewData])
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
      logger(lId, "avatarPostProgress", {"params": unbottle(request.params), "res": res});
    else:
      res["error"] = "no-line-matches-key"
  else:
    res["error"] = "no-key"
  return res
  
@route("/media/vcard", method="GET")
def media_vCard_get():
  cId = request.params.cId
  mId = request.params.mId
  chat = Chats.find_one({"_id": cId, "messages": {"$elemMatch": {"id": mId}}}, {"messages.$": 1})
  if chat:
    card = chat["messages"][0]["media"]["card"]
    caption = chat["messages"][0]["body"]
    response.set_header("Content-Type", "text/x-vcard; charset=UTF-8")
    response.set_header("Content-Disposition", "attachment; filename=%s.vcf" % urllib.quote_plus(caption.encode('utf8','replace')))
    return card
    
@route("/media/vcard", method="POST")
def media_vCard_post():
  res = {"success": False}
  key = request.params.key
  name = request.params.name.encode('utf8','replace')
  src = request.params.src
  to = request.params.to
  honor = request.params.honor
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      lId = line["_id"]
      logger(lId, "avatarPost", unbottle(request.params));
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if lineIsNotExpired(line):
        if token:
          if "permissions" in token and "write" in token["permissions"]:
            if name and src and to:
              if line["_id"] in running:
                wa = running[line["_id"]]["yowsup"]
                card_data = base64.b64decode(src)
                if not honor:
                  to = phoneFormat(line["cc"], to)
                idx = wa.call("media_vcard_send", (name, card_data, to))
                if idx:
                  res["result"] = idx
                  res["success"] = True
                  chat = Chats.find_one({"from": lId, "to": to})
                  stamp = long(time.time()*1000)
                  msg = {
                    "id": idx,
                    "mine": True,
                    "body": name,
                    "stamp": stamp,
                    "ack": "sent",
                    "media": {
                      "type": "vcard",
                      "card": card_data
                    }
                  }
                  if chat:
                    # Push it
                    Chats.update({"from": lId, "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp, "unread": 0}});
                  else:
                    # Create new chat
                    Chats.insert({
                      "_id": str(objectid.ObjectId()),
                      "from": lId,
                      "to": to,
                      "messages": [msg],
                      "lastStamp": stamp
                    })
                  runningTokens = running[line["_id"]]["tokens"]
                  for token in line["tokens"]:
                    if token["key"] in runningTokens:
                      if token["push"] and token["key"] != key:
                        url = "https://api.wha.tools/v%s/?cId=%s&mId=%s" % (v, chat["_id"], msg["id"])
                        pushRes = push(lId, token, "media_carbon", {"messageId": idx, "jid": to, "type": type, "name": name, "url": url, "timestamp": stamp})
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
      logger(lId, "avatarPostProgress", {"params": unbottle(request.params), "res": res});
    else:
      res["error"] = "no-line-matches-key"
  else:
    res["error"] = "no-key"
  return res
  
@route("/media/location", method="GET")
def media_location_get():
  cId = request.params.cId
  mId = request.params.mId
  format = request.params.format if request.params.format in ["gpx", "kml"] else "gpx"
  chat = Chats.find_one({"_id": cId, "messages": {"$elemMatch": {"id": mId}}}, {"messages.$": 1})
  if chat:
    media = chat["messages"][0]["media"]
    caption = chat["messages"][0]["body"] if "body" in chat["messages"][0] else "Location"
    response.set_header("Content-Type", "application/octet-stream; charset=UTF-8")
    response.set_header("Content-Disposition", "attachment; filename=%s.%s" % (urllib.quote_plus(caption.encode('utf8','replace')), format))
    if format == "kml":
      root = etree.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
      document = etree.Element("Document")
      placemark = etree.Element("Placemark")
      name = etree.Element("name")
      name.text = caption
      placemark.append(name)
      point = etree.Element("Point")
      coordinates = etree.Element("coordinates")
      coordinates.text = "%s,%s,0" % (media["latitude"], media["longitude"])
      point.append(coordinates)
      placemark.append(point)
      document.append(placemark)
      root.append(document)
    else:
      root = etree.Element("gpx", version="1.0")
      name = etree.Element("name")
      name.text = caption
      root.append(name)
      wpt = etree.Element("wpt", lat=media["latitude"], lon=media["longitude"])
      wpt_name = etree.Element("name")
      wpt_name.text = caption
      wpt.append(wpt_name)
      root.append(wpt)
    return etree.tostring(root, pretty_print = True, xml_declaration = True, encoding='UTF-8')
  
'''

STATIC CONTENT

'''

@route("/reference", method="GET")
def reference():
  return static_file('reference.htm', './static')
  
@route("/", method="GET")
def index():
  return static_file('reference.htm', './static')

recover(list(Lines.find({"tokens.active": True, "api": v}, {"tokens.$": 1})))
run(host="127.0.0.1", port="8081", server='gevent')
