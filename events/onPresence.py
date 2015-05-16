from helpers import *

def onPresence(wa, _type, _from, last):
  if last is not None and last.isdigit():
    to = _from.split("@")[0]
    db.Chats.update({"to": to}, {"$set": {"lastSeen": int(last)}})
