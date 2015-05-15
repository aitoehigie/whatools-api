from helpers import *

def onMessageReceived(wa, messageId, jid, participant, messageContent, timestamp, pushName, isBroadCast):
  to = jid.split("@")[0]
  chat = db.Chats.find_one({"from": wa.line["_id"], "to": to})
  stamp = int(timestamp)*1000
  msg = {
    "id": messageId,
    "mine": False,
    "body": messageContent,
    "stamp": stamp
  }
  if participant:
    msg["participant"] = participant
    msg["pushName"] = pushName
  if isBroadCast:
    msg["broadcast"] = broadcast
  if chat:
    # Push it to db
    db.Chats.update({"from": wa.line["_id"], "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp, "folder": "inbox"}, "$inc": {"unread": 1}})
  else:
    alias = False if participant else (pushName or False)
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
    if wa.line["_id"] in running:
      runningTokens = running[wa.line["_id"]]["tokens"]
      for token in allTokens:
        if token["key"] in runningTokens:
          if token["push"]:
            pushData = {"messageId": messageId, "jid": jid, "messageContent": messageContent, "timestamp": timestamp}
            if participant:
              pushData["participant"] = participant
            if isBroadCast:
              pushData["broadcast"] = broadcast
            res = push(wa.line["_id"], token, "message", pushData)
            if res:
              print res.read()
    else:
      print "WEIRD ERROR, message received for line not running"
  return True
