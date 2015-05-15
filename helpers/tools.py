import db, time, phonenumbers

def lineIsNotExpired(line):
  now = int(time.time()*1000)
  return now < int(line["expires"])

def logger(lId, event, data={}):
  if lId and event:
    db.Logs.insert({"line": lId, "stamp": int(time.time())*1000, "event": event, "data": data})

def messageSign(text, line):
  if line["plan"] == "free":
    if len(text) > 0:
      text += freePlanSignature
    else:
      text = freePlanSignature
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
