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
    line = db.Lines.find_one({"_id": wa.line["_id"]})
    if "reconnecting" not in g.running[line["_id"]] or not g.running[line["_id"]]["reconnecting"]:
      print "???? RECONNECTING!"
      def cb(wa, loginRes, data = None):
        g.running[line["_id"]]["yowsup"] = wa
        g.running[line["_id"]]["reconnecting"] = False
      g.running[line["_id"]]["reconnecting"] = True
      newWa = YowsupAsyncStack(line, line["tokens"][0], wa.getProp(AsyncLayer.HANDLERS), logger, cb)
      if newWa:
        gevent.spawn(newWa.login)
