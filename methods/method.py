import json
from gevent import queue
from helpers.bot import *
from helpers.tools import *

class method(object):

  errorMessages = {
    "user": "bad-user",
    "key": "no-key",
    "line": "no-line-matches-key",
    "version": "wrong-api-version",
    "expired": "line-is-expired",
    "token": "not-token-matches-key",
    "permission": "no-permission",
    "param": "bad-param",
    "inactive": "inactive-line"
  }

  def __init__(self, request, running, checks):
    self.request = request
    self.running = running
    self.checks = checks
    self.params = self.request.params
    
    self.key = request.params.key
    self.line = db.Lines.find_one({"tokens": {"$elemMatch": {"key": self.key}}}) if self.key else None
    self.token = filter(lambda e: e['key'] == self.key, self.line['tokens'])[0] if self.line else None
    self.wa = self.running[self.line["_id"]]["yowsup"] if self.line and self.line["_id"] in self.running else None
    self.expired = not lineIsNotExpired(self.line) if self.line else None
    
    self.error = False
    self.queue = queue.Queue()
    
    self._check()
    
  def _check(self):
    for check in self.checks:
      if type(check) is str:
        if any([
          check == "user" and not ("user" in self.params and db.Users.find_one({"_id": self.params.user})),
          check == "key" and not self.key,
          check == "line" and not self.line,
          check == "expired" and self.expired,
          check == "token" and not self.token,
          check == "inactive" and not self.line["_id"] in self.running
          ]):
          self.error = self.errorMessages[check]
          break
      elif type(check) is list:
        checker = check[0]
        payload = check[1]
        if any([
          checker == "version" and self.line["api"] != payload,
          checker == "permission" and ("permissions" not in self.token or payload not in self.token["permissions"]),
          checker == "param" and payload not in self.request.params,
          checker == "file" and not self.request.files.get(payload)
        ]):
          self.error = self.errorMessages[checker]
    if self.error:
      self._die(self.error)
    if self.expired:
      db.Lines.update({"_id": self.line["_id"]}, {"$set": {"valid": "wrong", "reconnect": False, "active": False}})

  def _log(self, title, payload = None):
    if self.line:
      logger(self.line["_id"], title, payload or unbottle(self.request.params))
    
  def _success(self, res = None):
    obj = {"success": True}
    if res is not None:
      obj["result"] = res
    self.queue.put(json.dumps(obj))
    self.queue.put(StopIteration)
    
  def _die(self, error):
    self.queue.put(json.dumps({"success": False, "error": error}))
    self.queue.put(StopIteration)
    
  def push(self, method, data):
    runningTokens = self.running[self.line["_id"]]["tokens"]
    for token in self.line["tokens"]:
      if token["key"] in runningTokens:
        if token["push"] and token["key"] != self.key:
          pushRes = push(self.line["_id"], token, method, data)
          if pushRes:
            logger(self.line["_id"], "pushResult", pushRes.read())
