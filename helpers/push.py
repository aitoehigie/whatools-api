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
  headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
  if url[0] == "https":
    conn = httplib.HTTPSConnection(url[1], int(url[2]))
  else:
    conn = httplib.HTTPConnection(url[1], int(url[2]))
  try:
    conn.sock.settimeout(3.0)
    logger(lId, "hookPost", {"url": url, "params": params, "headers": headers})
    conn.request("POST", '/' + url[3], params, headers)
    res = conn.getresponse()
  except:
    logger(lId, "hookProgress", {"success": False, "url": url, "params": params, "headers": headers})
    print "[PUSH] Connection refused while trying to " + method
  else:  
    logger(lId, "hookProgress", {"success": True, "result": res.read(), "url": url, "params": params, "headers": headers})
  return res
