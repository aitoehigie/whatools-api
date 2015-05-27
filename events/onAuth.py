import gevent
from helpers import *
from helpers.tools import *
from client.stack import YowsupAsyncStack
from client.layer import AsyncLayer

def onAuthFailed(wa):
  db.Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": False, "reconnect": False, "valid": False}});

def onAuthSuccess(wa):
  db.Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": True, "reconnect": True, "valid": True}});
  
def onDisconnected(wa, reason):
  print "???? DISCONNECTION", reason, wa.line["active"], wa.line["reconnect"], wa.line["_id"]
  logger(wa.line["_id"], "onDisconnected", {"reason": reason})
  if reason != "Requested" and wa.line["active"] and wa.line["reconnect"]:
    @delay(3.0)
    def reconnect():
      print "???? RECONNECTING!"
      line = db.Lines.find_one({"_id": wa.line["_id"]})
      def cb(wa, loginRes, data = None):
        if line["_id"] in g.running:
          g.running[line["_id"]]["yowsup"] = wa
      newWa = YowsupAsyncStack(line, line["tokens"][0], wa.getProp(AsyncLayer.HANDLERS), logger, cb)
      if newWa:
        gevent.spawn(newWa.login)
    reconnect()
