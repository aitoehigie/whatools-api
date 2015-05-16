import gevent
from helpers import *
from helpers.tools import *
from client.stack import YowsupAsyncStack
from client.layer import AsyncLayer

def onAxolotlReady(wa):
  line = db.Lines.find_one({"_id": wa.line["_id"]})
  def cb(wa, loginRes, data = None):
    if line["_id"] in g.running:
      g.running[line["_id"]]["yowsup"] = wa
  newWa = YowsupAsyncStack(line, line["tokens"][0], wa.getProp(AsyncLayer.HANDLERS), logger, cb)
  if newWa:
    gevent.spawn(newWa.login)
