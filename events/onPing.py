from helpers import *

def onPing(wa, pingId):
  line = wa.line
  if (not lineIsNotExpired(line)):
    db.Lines.update({"_id": lId}, {"$set": {"valid": "wrong", "reconnect": False, "active": False}})
    wa = running[line["_id"]]["yowsup"]
    wa.logout()
    # TODO: Notify expiracy to active tokens
    del running[line["_id"]]
  else:
    logger(line["_id"], "onPing", [pingId])
