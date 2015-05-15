from method import method
from helpers import db
from helpers.tools import *
import time

class messagePostMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "expired", "token", ["permission", "write"], ["param", "to"], ["param", "body"], "inactive"]
    super(messagePostMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("messagePost")
    to = self.params.to
    body = self.params.body.encode('utf-8').strip()
    signedBody = messageSign(body, self.line)
    broadcast = self.params.broadcast
    if not self.params.honor:
      to = phoneFormat(self.line["cc"], to)
    chat = db.Chats.find_one({"from": self.line["_id"], "to": to})
    if chat and not len(chat["messages"]):
      self.wa.call("presence_subscribe", [to])
    msgId = self.wa.call("message_send", [to, signedBody])
    if msgId:
      self._success(msgId)
      stamp = int(time.time() * 1000)
      msg = {"id": msgId, "mine": True, "body": body, "stamp": stamp, "ack": "sent"}
      if chat:
        db.Chats.update({"from": self.line["_id"], "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp, "unread": 0}})
      else:
        db.Chats.insert({"_id": str(objectid.ObjectId()), "from": self.line["_id"], "to": to, "messages": [msg], "lastStamp": stamp, "folder": "inbox"})
      self.push("carbon", {"messageId": msgId, "jid": to, "messageContent": body, "timestamp": stamp, "isBroadCast": broadcast})
