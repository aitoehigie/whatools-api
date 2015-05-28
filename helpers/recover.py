import db, gevent
from gevent import monkey; monkey.patch_all()
from tools import *
from events import *
from client.stack import YowsupAsyncStack

def recover(lines=False):
  if lines:
    for line in lines:
      done = [False]
      count = 0
      res = {"success": False}
      tokens = line["tokens"]
      fullLine = db.Lines.find_one({"_id": line["_id"]})
      user = fullLine["cc"] + fullLine["pn"]
      logger(line["_id"], "lineRecover", [user]);
      print "@@@ RECOVERING LINE +%s @@@" % user
      def cb(wa, loginRes, data = None):
        if loginRes == "success":
          if fullLine["_id"] not in running:
            running[fullLine["_id"]] = {
              "yowsup": wa,
              "tokens": []
            }
          for token in tokens:
            if token["active"]:
              running[fullLine["_id"]]["tokens"].append(token["key"])
          print "@@@@ RECOVER SUCCESS +%s @@@@" % user
          print running
          res["success"] = True
        else:
          print "@@@@ RECOVER ERROR +%s @@@@" % user
          res["error"] = "auth-error"
        logger(fullLine["_id"], "lineRecoverProgress", {"res": res})
        done[0] = True
      wa = YowsupAsyncStack(fullLine, tokens[0], eventHandler, logger, cb)
      if wa:
        gevent.Greenlet.spawn(wa.login)
      else:
        res["error"] = "connect-error"
        logger(fullLine["_id"], "lineRecoverProgress", {"res": res})
        print "@@@@ RECOVER ERROR @@@@"
      while not done[0] and count < 20:
        gevent.sleep(.5)
        count += 1
  return
