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
      token = line["tokens"][0]
      fullLine = db.Lines.find_one({"_id": line["_id"]})
      user = fullLine["cc"] + fullLine["pn"]
      logger(line["_id"], "lineRecover", [token]);
      print "@@@ RECOVERING TOKEN {0} FOR LINE {1} @@@".format(token["key"], line["_id"])
      def cb(wa, loginRes, data = None):
          if loginRes == "success":
            if fullLine["_id"] in running:
              running[fullLine["_id"]]["tokens"].append(token["key"])
            else:
              running[fullLine["_id"]] = {
                "yowsup": wa,
                "tokens": [token["key"]]
              }
            print "@@@@ RECOVER SUCCESS @@@@ {0} {1}".format(token["key"], line["_id"])
            res["success"] = True
          else:
            print "@@@@ RECOVER ERROR @@@@ {0} {1}".format(token["key"], line["_id"])
            res["error"] = "auth-error"
          logger(fullLine["_id"], "lineRecoverProgress", {"res": res});
          done[0] = True
      wa = YowsupAsyncStack(fullLine, token, eventHandler, logger, cb)
      if wa:
        gevent.Greenlet.spawn(wa.login)
      else:
        res["error"] = "connect-error"
        logger(fullLine["_id"], "lineRecoverProgress", {"res": res});
        print "@@@@ RECOVER ERROR @@@@"
  return
