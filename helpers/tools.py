import db, time, phonenumbers, g, threading
from functools import wraps

def lineIsNotExpired(line):
  now = int(time.time()*1000)
  return now < int(line["expires"])

def logger(lId, event, data={}):
  if lId and event:
    db.Logs.insert({"line": lId, "stamp": int(time.time())*1000, "event": event, "data": data})

def messageSign(text, line):
  if line["plan"] == "free":
    if len(text) > 0:
      text += g.freePlanSignature
    else:
      text = g.freePlanSignature
  return text

def phoneFormat(cc, pn):
  region = phonenumbers.region_code_for_country_code(int(cc))
  parsed = phonenumbers.parse(pn, region)
  formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
  clean = formatted.replace("+", "")
  return clean

def unbottle(data):
  dataDict = {}
  for item in data:
    dataDict[item] = data[item]
  return dataDict
  
def delay(delay=0.):
  """
  Decorator delaying the execution of a function for a while.
  Original code by Fred Wenzel (http://fredericiana.com)
  """
  def wrap(f):
    @wraps(f)
    def delayed(*args, **kwargs):
      timer = threading.Timer(delay, f, args=args, kwargs=kwargs)
      timer.start()
    return delayed
  return wrap
