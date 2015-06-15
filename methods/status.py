from method import method
from helpers import db
import time

class statusGetMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "expired", "token", ["permission", "read"]]
    super(statusGetMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("statusGet")
    self._success(self.line["statusMessage"] if "statusMessage" in self.line else False)


class statusPostMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "expired", "token", ["permission", "write"], ["param", "message"], "active"]
    super(statusPostMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("statusPost")
    
    def success(resultIq, requestIq):
      db.Lines.update({"_id": self.line["_id"]}, {"$set": {"statusMessage": self.message}})
      self._log("statusPostSuccess")
      self._success()
      
    def fail(errorIq, requestIq):
      self._log("statusPostError")
      self._die()
    
    self.message = self.params.message.encode("utf-8", "replace").strip()
    self.wa.call("profile_setStatus", [self.message, success, fail])
