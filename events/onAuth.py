from helpers import *

def onAuthFailed(wa):
  db.Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": False, "reconnect": False, "valid": False}});

def onAuthSuccess(wa):
  db.Lines.update({"_id": wa.line["_id"]}, {"$set": {"active": True, "reconnect": True, "valid": True}});
  
def onDisconnected(wa, reason):
  print "???? DISCONNECTION", reason, line["active"], line["reconnect"], line["_id"]
