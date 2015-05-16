import gevent
from helpers import *
from events import eventHandler
from client.stack import YowsupAsyncStack

def onAxolotlReady(wa):
  line = db.Lines.find_one({"_id": wa.line["_id"]})
  def cb(wa, loginRes, data = None):
    if line["_id"] in g.running:
      g.running[line["_id"]]["yowsup"] = wa
  newWa = YowsupAsyncStack([line["cc"] + line["pn"], line["pass"]], line, line["tokens"][0], eventHandler, logger, cb)
  if newWa:
    gevent.spawn(newWa.login)
