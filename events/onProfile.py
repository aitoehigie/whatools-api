from helpers import *

def onProfileSetPictureError(wa, idx, errorCode):
  if idx in uploads:
    allTokens = db.Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens and token["key"] == uploads[idx]["token"] and token["push"]:
        res = push(wa.line["_id"], token, "error", {"type": "onProfileSetPictureError", "idx": idx})
    del uploads[idx]

def onProfileSetPictureSuccess(wa, idx, pictureId):
  if idx in uploads:
    line = wa.line
    src = uploads[idx]["src"]
    item = {
      "src": src,
      "id": pictureId
    }
    db.Avatars.update({"jid": line["cc"] + line["pn"]}, {"$push": {"items": item}}, True)
    allTokens = db.Lines.find_one({"_id": wa.line["_id"]})["tokens"]
    runningTokens = running[wa.line["_id"]]["tokens"]
    for token in allTokens:
      if token["key"] in runningTokens and token["key"] == uploads[idx]["token"] and token["push"]:
          res = push(wa.line["_id"], token, "success", {"type": "onProfileSetPictureSuccess", "idx": idx, "pictureId": pictureId})
    del uploads[idx]
  else:
    print "COULD NOT RECOVER idx %s" % idx
    print uploads

def onProfileSetStatusSuccess(wa, jid, idx):
  allTokens = db.Lines.find_one({"_id": wa.line["_id"]})["tokens"]
  runningTokens = running[wa.line["_id"]]["tokens"]
  for token in allTokens:
    if token["key"] in runningTokens and token["push"]:
        res = push(wa.line["_id"], token, "success", {"type": "onProfileSetStatusSuccess", "idx": idx})
