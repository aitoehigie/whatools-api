from methods.method import method
from helpers import *
import time, urllib

class mediaVcardGetMethod(method):

  def __init__(self, request, running, response = None):
    checks = [["param", "cId"], ["param", "mId"]]
    super(mediaVcardGetMethod, self).__init__(request, running, checks)
    self.response = response
    if not self.error:
      self.run()
    
  def run(self):
    self._log("mediaVcardGet")
    chat = db.Chats.find_one({"_id": self.params.cId, "messages": {"$elemMatch": {"id": self.params.mId}}}, {"messages.$": 1})
    if chat:
      card = chat["messages"][0]["media"]["card"]
      caption = chat["messages"][0]["body"]
      if self.response:
        self.response.set_header("Content-Type", "text/x-vcard; charset=UTF-8")
        self.response.set_header("Content-Disposition", "attachment; filename=%s.vcf" % urllib.quote_plus(caption.encode('utf8','replace')))
      self.queue.put(card)
      self.queue.put(StopIteration)
    else:
      self._die("file-not-found")

class mediaVcardPostMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "expired", "token", ["permission", "write"], ["param", "name"], ["param", "src"], ["param", "to"], "active"]
    super(mediaVcardPostMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("mediaVcardPost")
    name = self.params.name.encode("utf-8", "replace").strip()
    src = self.params.src
    to = self.params.to
    honor = self.params.honor
    broadcast = self.params.broadcast
    card_data = src.decode("base64")
    if not honor:
      to = phoneFormat(self.line["cc"], to)
    jid = self.wa.normalizeJid(to)
    chat = db.Chats.find_one({"from": self.line["_id"], "to": to})
    
    def success(inNumbers = [], outNumbers = [], invalidNumbers = []):
      if jid in inNumbers.values():
        msgId = self.wa.call("media_vcard_send", (name, card_data, to))
        if msgId:
          self._success(msgId)
          stamp = int(time.time() * 1000)
          msg = {"id": msgId, "mine": True, "body": name, "stamp": stamp, "ack": "sent", "media": {"type": "vcard", "card": card_data}}
          chat = db.Chats.find_one({"from": self.line["_id"], "to": to})
          if chat:
            db.Chats.update({"from": self.line["_id"], "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp, "unread": 0}})
          else:
            db.Chats.insert({"_id": str(objectid.ObjectId()), "from": self.line["_id"], "to": to, "messages": [msg], "lastStamp": stamp, "folder": "inbox"})
          self.push("media_carbon", {"id": msgId, "to": to, "body": name, "timestamp": stamp, "broadcast": broadcast})
      elif jid in outNumbers.values():
        self._log("mediaVcardPostError")
        self._die("phone-number-not-in-whatsapp", 404)
      else:
        self._log("mediaVcardPostError")
        self._die("malformed-phone-number", 400)

    def error(errorEntity, requestEntity):
      self._log("mediaVcardPostError")
      self._die("request-error", 400)
    
    if chat and len(chat["messages"]):
      success({"0": jid})
    else:
      self.wa.call("contact_sync", [["+" + to], "delta", "interactive", success, error])
