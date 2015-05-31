import time
from helpers import *

def onNotificationDeletePicture(wa, jid, deleteJid):
  setJid = setJid.split("@")[0]
  avatars = db.Avatars.find_one({"jid", setJid})
  if avatars:
    items = avatars["items"]
    for index, item in enumerate(items):
      if item["id"] == setId:
        items.pop(index)
        break
  return True
  
def onNotificationSetPicture(wa, jid, setJid, setId):
  items = []
  setJid = setJid.split("@")[0]
  
  def success(item):
    items.append(item)
    db.Avatars.update({"jid": setJid}, {"$set": {"items": items}}, True)
    
  def iqSuccess(resultIq, requestIq):
    name = "avatars/%s-%s.jpg" % (setJid, resultIq.getPictureId())
    path = "%s%s" % (g.storage, name)
    resultIq.writeToFile(path)
    item = {"src": name, "id": resultIq.getPictureId()}
    success(item)
    
  def iqError(errorIq, requestIq):
    pass
  
  avatars = db.Avatars.find_one({"jid": setJid})
  if avatars:
    items = avatars["items"]
    found = False
    for index, item in enumerate(items):
      if item["id"] == setId:
        items.pop(index)
        found = True
        success(item)
        break
    if not found:
      wa.call("profile_getPicture", [setJid, iqSuccess, iqError])
  else:
    wa.call("profile_getPicture", [setJid, iqSuccess, iqError])
  
  return True
