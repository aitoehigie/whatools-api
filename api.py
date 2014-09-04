import json, base64
from bottle import route, run, request
from pymongo import MongoClient
from Yowsup.Common.utilities import Utilities
from Yowsup.Common.debugger import Debugger
from Yowsup.Common.constants import Constants
from Examples.EchoClient import WhatsappEchoClient
from Examples.GetClient import WhatsappGetClient
from Yowsup.Contacts.contacts import WAContactsSyncRequest

client = MongoClient()
db = client.waapi

Users = db.users
Lines = db.lines

'''@route("/messages", method="GET")
def messages_get():
  res = {"success": False}
  key = request.params.key
  ack = request.params.ack
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}});
    if line:
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if token:
        if "permissions" in token and "read" in token["permissions"]:
          wa = WhatsappGetClient(False, ack)
          messages = wa.login(str(line["pn"]), str(base64.b64decode(bytes(line["pw"].encode('utf-8')))))
          res["list"] = messages
          res["success"] = True
        else:
          res["error"] = "no-permission"
      else:
        res["error"] = "no-token"
    else:
      res["error"] = "invalid-key"
  else:
    res["error"] = "no-key"
  return res'''

@route("/messages", method="POST")
def messages_post():
  res = {"success": False}
  key = request.params.key
  to = request.params.to
  body = request.params.body
  ack = request.params.ack
  if key:
    line = Lines.find_one({"tokens": {"$elemMatch": {"key": key}}});
    if line:
      token = filter(lambda e: e['key'] == key, line['tokens'])[0]
      if token:
        if "permissions" in token and "write" in token["permissions"]:
          if to and body:
            wa = WhatsappEchoClient(to, str(body), ack)
            wa.login(str(line["pn"]), str(base64.b64decode(bytes(line["pw"].encode('utf-8')))))
            res["success"] = True
          else:
            res["error"] = "wrong-params"
        else:
          res["error"] = "no-permission"
      else:
        res["error"] = "no-token"
    else:
      res["error"] = "invalid-key"
  else:
    res["error"] = "no-key"
  return res


run(host="192.168.2.2", port="8080", debug=True)
