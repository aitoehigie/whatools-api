from method import method
from helpers import db
import time

class nicknameGetMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "token", ["permission", "read"]]
    super(nicknameGetMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("nicknameGet")
    self._success(self.line["nickname"] if "nickname" in self.line else False)


class nicknamePostMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "expired", "token", ["permission", "write"], ["param", "nickname"], "active"]
    super(nicknamePostMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("nicknamePost")
    nickname = self.params.nickname.encode('utf-8').strip()
    self.wa.call("presence_sendAvailable", [nickname])
    db.Lines.update({"_id": self.line["_id"]}, {"$set": {"nickname": nickname}})
    self._success()
