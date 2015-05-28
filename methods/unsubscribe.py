from method import method
from helpers import db
import time

class unsubscribeGetMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "token", "inactive"]
    super(unsubscribeGetMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("unsubscribeGet")
    db.Lines.update({"_id": self.line["_id"], "tokens.key": self.token["key"]}, {"$set": {"tokens.$.active": False}})
    if self.token["key"] in self.running[self.line["_id"]]["tokens"]:
      self.running[self.line["_id"]]["tokens"].remove(self.token["key"])
    if len(self.running[self.line["_id"]]["tokens"]) < 1:
      db.Lines.update({"_id": self.line["_id"]}, {"$set": {"reconnect": False, "active": False}})
      if self.line["_id"] in self.running:
        del self.running[self.line["_id"]]
      self.wa.logout()
    self._success()
