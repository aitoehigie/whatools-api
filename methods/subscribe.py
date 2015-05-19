from method import method
from helpers import db, g, logger
from events import eventHandler
from client.stack import YowsupAsyncStack
import time, base64, gevent

class subscribeGetMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", ["version", g.v], "expired", "token", ["permission", "write"]]
    super(subscribeGetMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("subscribeGet")
    
    def cb(wa, loginRes, data = None):
      # Enable token and line
      if loginRes:
        if self.token["key"] not in self.running[self.line["_id"]]["tokens"]:
          self.running[self.line["_id"]]["tokens"].append(self.token["key"])
        db.Lines.update({"_id": self.line["_id"], "tokens.key": self.token["key"]}, {"$set": {"valid": True, "active": True, "tokens.$.active": True}})
        if data:
          db.Lines.update({"_id": self.line["_id"]}, {"$set": {"data": data}})
        # Prepare the result data
        result = data
        result["cc"] = self.line["cc"]
        result["pn"] = self.line["pn"]
        result["api_expiration"] = int(self.line["expires"] / 1000)
        if "props" in result:
          del result["props"]
        # Update presence
        self.wa.call("presence_sendAvailable", [self.line["nickname"] if "nickname" in self.line else None])
        self._log("subscribeGetSuccess", result)
        self._success(result)
      else:
        del self.running[self.line["_id"]]
        db.Lines.update({"_id": self.line["_id"], "tokens.key": self.token["key"]}, {"$set": {"valid": "wrong", "reconnect": False, "tokens.$.active": False}})
        self._log("subscribeGetError")
        self._die("auth-failed", 401)
    
    if self.wa is not None:
      cb(self.wa, True, self.line["data"])
    else:
      self.wa = YowsupAsyncStack(self.line, self.token, eventHandler, logger, cb)
      try:
        pw = base64.b64decode(bytes(str(self.line["pass"])))
      except TypeError:
        self._die("password-type-error", 401)
        db.Lines.update({"_id": self.line["_id"], "tokens.key": self.token["key"]}, {"$set": {"valid": "wrong", "reconnect": False, "tokens.$.active": False}})
      self.running[self.line["_id"]] = {
        "yowsup": self.wa,
        "tokens": [self.token["key"]]
      }
      gevent.spawn(self.wa.login)

