from helpers import *
import time, base64

def onMediaReceived(wa, messageId, jid, participant, caption, type, preview, url, size, notify, isBroadCast):
  to = jid.split("@")[0]
  chat = db.Chats.find_one({"from": wa.line["_id"], "to": to})
  stamp = int(time.time())*1000
  msg = {
    "id": messageId,
    "mine": False,
    "stamp": stamp,
    "media": {
      "location": {
        "type": "location",
        "preview": base64.b64encode(preview) if preview else None,
        "latitude": url,
        "longitude": size
      },
      "vcard": {
        "type": "vcard",
        "card": preview
      }
    }.get(type, {
      "type": type,
      "preview": base64.b64encode(preview) if preview else None,
      "url": url,
      "size": size
    })
  }
  if caption:
    msg["body"] = caption
  if participant:
    msg["participant"] = participant
  if isBroadCast:
    msg["broadcast"] = broadcast
  if chat:
    # Push it to db
    db.Chats.update({"from": wa.line["_id"], "to": to}, {"$set": {"folder": "inbox"}, "$push": {"messages": msg}, "$set": {"lastStamp": stamp, "folder": "inbox"}, "$inc": {"unread": 1}});
  else:
    alias = False if participant else (notify or False)
    # Create new chat
    db.Chats.insert({
      "_id": str(objectid.ObjectId()),
      "from": wa.line["_id"],
      "to": to,
      "messages": [msg],
      "lastStamp": stamp,
      "alias": alias,
      "folder": "inbox"
    })
  bot.botify(wa, msg, to, running)
  if len(running):
    allTokens = db.Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens:
        if token["push"]:
          if type == "location":
            pushData = {"id": messageId, "from": jid.split("@")[0], "type": type, "preview": base64.b64encode(preview), "latitude": url, "longitude": size, "timestamp": stamp}
          elif type == "vcard":
            url = "https://api.wha.tools/v%s/?cId=%s&mId=%s" % (v, chat["_id"], msg["id"])
            pushData = {"id": messageId, "from": jid.split("@")[0], "type": type, "name": caption, "url": url, "timestamp": stamp}
          else:
            pushData = {"id": messageId, "from": jid.split("@")[0], "type": type, "preview": base64.b64encode(preview), "url": url, "size": size, "timestamp": stamp}
            if caption:
              pushData["caption"] = caption
          if participant:
            pushData["participant"] = participant.split("@")[0]
          if isBroadCast:
            pushData["broadcast"] = broadcast
          if notify:
            pushData["nickname"] = notify
          pushRes = push(wa.line["_id"], token, "media", pushData)
          if pushRes:
            print pushRes.read()
  return True;
