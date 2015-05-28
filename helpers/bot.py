#!/usr/bin/python
#  -*- coding: utf8 -*-
import sys, re, time, urllib
import db
from tools import *

reload(sys)
sys.setdefaultencoding('utf8')

class Bot(object):

  ops = {
    'or': lambda a, b: a or b,
    'and': lambda a, b: a and b,
    'xor': lambda a, b: a ^ b
  }

  verbs = {
    'yes': lambda subj, obj: True,
    'exists': lambda subj, obj: subj is not None,
    'is': lambda subj, obj: str(subj) == str(obj),
    'starts': lambda subj, obj: re.compile('^%s' % str(obj)).search(str(subj)) is not None,
    'ends': lambda subj, obj: re.compile('%s$' % str(obj)).search(str(subj)) is not None,
    'contains': lambda subj, obj: re.compile(str(obj)).search(str(subj)) is not None,
    'lt': lambda subj, obj: subj < obj,
    'gt': lambda subj, obj: subj > obj
  }

  def evaluate(self, msg, conditions):
    return reduce(lambda prev, cur: self.ops[cur["op"]](prev, cur["sign"] == (cur["verb"] in self.verbs and cur["subj"] in msg and self.verbs[cur["verb"]](msg[cur["subj"]], cur["obj"]))), conditions, 0)

  def run(self, message, conditions, consequences, actions):
    if conditions == False or self.evaluate(message, conditions):
      for consequence in consequences:
        actions[consequence["action"]](message, consequence[consequence["action"]])

def botify(wa, msg, pn, running):
  def action_answer(msg, payload):
    to = msg["from"]
    body = payload.encode('utf8','replace')
    stamp = int(time.time()*1000)
    chat = db.Chats.find_one({"from": wa.line["_id"], "to": to})
    msgId = wa.call("message_send", (msg["from"], messageSign(body, wa.line)))
    msg = {
      "id": msgId,
      "mine": True,
      "body": body,
      "stamp": stamp,
      "ack": "sent"
    }
    db.Chats.update({"from": wa.line["_id"], "to": to}, {"$push": {"messages": msg}})
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in wa.line["tokens"]:
      if token["key"] in runningTokens:
        if token["push"]:
          pushRes = push(wa.line["_id"], token, "carbon", {"messageId": msgId, "jid": to, "messageContent": body, "timestamp": stamp})
          if pushRes:
            print pushRes.read()
    
  def action_canned(msg, payload):
    to = msg["from"]
    canned = next((x for x in wa.line["canned"] if x["id"] == payload), "")
    if canned and len(canned):
      body = canned["body"].encode('utf8','replace')
      stamp = int(time.time()*1000)
      chat = db.Chats.find_one({"from": wa.line["_id"], "to": to})
      msgId = wa.call("message_send", (msg["from"], messageSign(body, line)))
      msg = {
        "id": msgId,
        "mine": True,
        "body": body,
        "stamp": stamp,
        "ack": "sent"
      }
      db.Chats.update({"from": wa.line["_id"], "to": to}, {"$push": {"messages": msg}})
      runningTokens = running[wa.line["_id"]]["tokens"]
      for token in wa.line["tokens"]:
        if token["key"] in runningTokens:
          if token["push"]:
            pushRes = push(wa.line["_id"], token, "carbon", {"messageId": msgId, "jid": to, "messageContent": body, "timestamp": stamp})
            if pushRes:
              print pushRes.read()
              
  def action_forward(msg, payload):
    to = phoneFormat(wa.line["cc"], payload)
    body = "♻ +%s:\n%s" % (msg["from"], msg["body"])
    stamp = msg["stamp"]
    chat = db.Chats.find_one({"from": wa.line["_id"], "to": to})
    msgId = wa.call("message_send", (to, messageSign(body, wa.line)))
    msg = {
      "id": msgId,
      "mine": True,
      "body": body,
      "stamp": stamp,
      "ack": "sent"
    }
    if chat:
      db.Chats.update({"from": wa.line["_id"], "to": to}, {"$set": {"folder": "inbox"}, "$push": {"messages": msg}, "$set": {"lastStamp": stamp}})
    else:
      db.Chats.insert({
        "_id": str(objectid.ObjectId()),
        "from": wa.line["_id"],
        "to": to,
        "messages": [msg],
        "lastStamp": stamp,
        "alias": False
      })
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in wa.line["tokens"]:
      if token["key"] in runningTokens:
        if token["push"]:
          pushRes = push(wa.line["_id"], token, "carbon", {"messageId": msgId, "jid": to, "messageContent": body, "timestamp": stamp})
          if pushRes:
            print pushRes.read()
            
  def action_post(msg, payload):
    to = msg["from"]
    url = payload
    stamp =  int(time.time()*1000)
    chat = db.Chats.find_one({"from": wa.line["_id"], "to": to})
    data = {
      "body": msg["body"]
    }
    params = urllib.urlencode(data)
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    if url.split("://")[0] == "https":
      conn = httplib.HTTPSConnection(url.split("/")[2], 443)
    else:
      conn = httplib.HTTPConnection(url.split("/")[2], 80)
    try:
      conn.request("POST", '/' + "/".join(url.split("/")[3:]), params, headers)
      res = conn.getresponse()
    except:
      pass
    else:
      answer = res.read()
      if len(answer):
        msgId = wa.call("message_send", (to, messageSign(answer, wa.line)))
        msg = {
          "id": msgId,
          "mine": True,
          "body": answer,
          "stamp": stamp,
          "ack": "sent"
        }
        if chat:
          db.Chats.update({"from": wa.line["_id"], "to": to}, {"$set": {"folder": "inbox"}, "$push": {"messages": msg}, "$set": {"lastStamp": stamp}})
        else:
          db.Chats.insert({
            "_id": str(objectid.ObjectId()),
            "from": wa.line["_id"],
            "to": to,
            "messages": [msg],
            "lastStamp": stamp,
            "alias": False
          })
        runningTokens = running[wa.line["_id"]]["tokens"]
        for token in wa.line["tokens"]:
          if token["key"] in runningTokens:
            if token["push"]:
              pushRes = push(wa.line["_id"], token, "carbon", {"messageId": msgId, "jid": to, "messageContent": answer, "timestamp": stamp})
              if pushRes:
                print pushRes.read()
    
  actions = {
    'answer': action_answer,
    'canned': action_canned,
    'forward': action_forward,
    'post': action_post
  }
  line = db.Lines.find_one({"_id": wa.line["_id"]})
  chat = db.Chats.find_one({"from": wa.line["_id"],  "to": pn})
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
        Bot().run(msg, bot["cond"], bot["cons"], actions)
        logger(line["_id"], "botProcess", msg)
