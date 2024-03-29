import db, httplib, urllib
from tools import *

def push(lId, token, method, data):
  res = False
  url = token["push"]
  line = db.Lines.find_one({"_id": lId})
  data["_lineId"] = "%s%s" % (line["cc"], line["pn"])
  data["_tokenId"] = token["id"]
  data["_method"] = method
  params = urllib.urlencode(data)
  headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
  if url[0] == "https":
    conn = httplib.HTTPSConnection(str(url[1]), int(url[2]), timeout=5)
  else:
    conn = httplib.HTTPConnection(str(url[1]), int(url[2]), timeout=5)
  try:
    logger(lId, "hookPost", {"url": url, "params": params, "headers": headers})
    conn.request("POST", "/%s" % str(url[3]), params, headers)
    res = conn.getresponse()
  except Exception as e:
    logger(lId, "hookProgress", {"success": False, "url": url, "params": params, "headers": headers})
    print "[WebHook] Connection refused while trying to call method %s" % method
    print e.__doc__
    print e.message
  else:  
    logger(lId, "hookProgress", {"success": True, "result": res.read(), "url": url, "params": params, "headers": headers})
  return res
