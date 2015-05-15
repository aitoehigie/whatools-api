from helpers import *

def onAck(wa, idx, jid, grade):
  print "ACK from " + jid + " to " + wa.line["cc"] + wa.line["pn"] + "type: " + grade
  if len(g.running):
    allTokens = db.Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    if wa.line["_id"] in g.running:
      runningTokens = g.running[wa.line["_id"]]["tokens"]
      message = db.Chats.find_one({"from": wa.line["_id"], "to": jid.split("@")[0], 'messages.id': idx}, {"messages.$": 1})
      if message:
        message = ["messages"][0]
        for token in allTokens:
          if token["key"] in runningTokens:
            if token["push"]:
              res = push(wa.line["_id"], token, "ack", {"grade": grade, "jid": jid, "messageId": idx})
              if res:
                print res.read()
    else:
      print "WEIRD ERROR, message received for line not running"
    db.Chats.update({"from": wa.line["_id"], "to": jid.split("@")[0], 'messages.id': idx}, {"$set": {'messages.$.ack': grade}})
    return True
