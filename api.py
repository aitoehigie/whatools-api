import json, base64
from bottle import route, run, request
from pymongo import MongoClient
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

running = {}

@route("/message", method="POST")
def messages_post():
  res = {"success": False}
  key = request.params.key
  to = request.params.to
  body = request.params.body.encode('ascii','replace')
  ack = request.params.ack
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}})
    if line:
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if token:
        if "permissions" in token and "write" in token["permissions"]:
          if to and body:
            if line["_id"] in running:
              wa = running[line["_id"]];
              wa.say(to, body, ack)
              res["success"] = True
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
          Lines.update({"_id": lId}, {"$set": {"validated": "wrong"}})
          return res
        res["success"] = True
        res["result"] = wa.login(user, pw)
        if (res["result"] == "valid"):
          Lines.update({"_id": lId}, {"$set": {"validated": True}})
        else:
          Lines.update({"_id": lId}, {"$set": {"validated": "wrong"}})
      else:
        res["error"] = "could-not-connect"
    else:
      res["error"] = "no-such-line"
  else:
    res["error"] = "bad-param"
  return res
  
@route("/line/run", method="GET")
def line_run():
  res = {"success": False}
  lId = request.params.id
  if lId:
    if lId in running:
      wa = running[lId]
      res["error"] = "already-running"
    else:
      line = Lines.find_one({"_id": lId})
      if line:
        wa = WhatsappBackClient()
        if wa:
          user = line["cc"] + line["pn"]
          try:
            pw = base64.b64decode(bytes(line["pass"].encode('utf-8')))
          except TypeError:
            res["error"] = "password-type-error"
            Lines.update({"_id": lId}, {"$set": {"validated": "wrong"}})
            return res
          loginRes = wa.login(user, pw)
          if (loginRes == "success"):
            res["success"] = True
            running[lId] = wa
          else:
            res["error"] = "auth-failed"
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
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if token:
        wa = WhatsappBackClient()
        if wa:
          user = line["cc"] + line["pn"]
          try:
            pw = base64.b64decode(bytes(line["pass"].encode('utf-8')))
          except TypeError:
            res["error"] = "password-type-error"
            Lines.update({"_id": lId}, {"$set": {"validated": "wrong"}})
            return res
          loginRes = wa.login(user, pw)
          if (loginRes == "success"):
            res["success"] = True
            running[lId] = wa
          else:
            res["error"] = "auth-failed"
        else:
          res["error"] = "could-not-connect"
      else:
        res["error"] = "no-token"
    else:
      res["error"] = "invalid-key"
  else:
    res["error"] = "no-key"
  return res

run(host="192.168.2.2", port="8080", debug=True, reloader=True)
