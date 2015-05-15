from method import method
from helpers import db
import time

class historyGetMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "token", ["permission", "manage"]]
    super(historyGetMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("historyGet")
    start = self.params.start or int(0)
    end = self.params.end or int(time.time() * 1000)
    obj = {"messages": [], "totals": {"all": 0, "in": 0, "out": 0}}
    myChats = db.Chats.find({"from": self.line["_id"]})
    for chat in myChats:
      for message in chat["messages"]:
        if int(message["stamp"]) >= int(start) and int(message["stamp"]) <= int(end):
          message["from"] = self.line["cc"] + self.line["pn"]
          message["to"] = chat["to"]
          obj["messages"].append(message)
          if message["mine"] == True:
            obj["totals"]["out"] += 1
          else:
            obj["totals"]["in"] += 1
    obj["totals"]["all"] = len(obj["messages"])
    self._success(obj)
