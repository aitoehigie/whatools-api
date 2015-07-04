from method import method
from helpers import db
from helpers.tools import *
from bson import objectid
from yowsup.common.constants import YowConstants
import time

class messagePostMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "expired", "token", ["permission", "write"], ["param", "to"], ["param", "body"], "active"]
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
    jid = self.wa.normalizeJid(to)
    chat = db.Chats.find_one({"from": self.line["_id"], "to": to})

    def success(inNumbers = [], outNumbers = [], invalidNumbers = []):
      if jid in inNumbers.values():
        msgId = self.wa.call("message_send", [to, signedBody])
        if msgId:
          self._success(msgId)
          stamp = int(time.time() * 1000)
          msg = {"id": msgId, "mine": True, "body": body, "stamp": stamp, "ack": "sent"}
          if chat:
            db.Chats.update({"from": self.line["_id"], "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp, "unread": 0, "folder": "inbox"}})
          else:
            db.Chats.insert({"_id": str(objectid.ObjectId()), "from": self.line["_id"], "to": to, "messages": [msg], "lastStamp": stamp, "folder": "inbox"})
            self.wa.call("presence_subscribe", [to])
          self.push("carbon", {"id": msgId, "to": to, "body": body, "timestamp": stamp, "broadcast": broadcast})
      elif jid in outNumbers.values():
        self._log("messagePostError")
        self._die("phone-number-not-in-whatsapp", 404)
      else:
        self._log("messagePostError")
        self._die("malformed-phone-number", 400)

    def error(errorEntity, requestEntity):
      self._log("messagePostError")
      self._die("request-error", 400)

    if chat and len(chat["messages"]):
      success({"0": jid})
    else:
      self.wa.call("contact_sync", [["+" + to], "delta", "interactive", success, error])
