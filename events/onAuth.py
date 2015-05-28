import gevent
from helpers import *
from helpers.tools import *
from client.stack import YowsupAsyncStack
from client.layer import AsyncLayer

def onAuthFailed(wa):
  db.Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": False, "reconnect": True, "valid": False}});

def onAuthSuccess(wa):
  db.Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": True, "reconnect": True, "valid": True}});
  
def onDisconnected(wa, reason):
  print "???? DISCONNECTION", reason, wa.line["active"], wa.line["reconnect"], wa.line["_id"], wa.line["cc"], wa.line["pn"]
  if reason != "Requested" and wa.line["reconnect"]:
    print "???? RECONNECTING!"
    line = db.Lines.find_one({"_id": wa.line["_id"]})
    g.running[line["_id"]]["yowsup"] = YowsupAsyncStack(line, line["tokens"][0], wa.getProp(AsyncLayer.HANDLERS), logger, cb)
    gevent.spawn(g.running[line["_id"]]["yowsup"].login)
