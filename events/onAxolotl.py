from helpers import *

def onAxolotlReady(wa):
  line = db.Lines.find_one({"_id": wa.line["_id"]})
  def cb(wa, loginRes, payload):
    if line["_id"] in running:
      running[line["_id"]]["yowsup"] = wa
  newWa = YowsupAsyncStack([line["cc"] + line["pn"], line["pass"]], line, line["tokens"][0], eventHandler, logger, cb)
  if newWa:
    gevent.spawn(newWa.login)
