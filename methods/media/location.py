from methods.method import method
from helpers import *
import time, urllib, base64
from lxml import etree

class mediaLocationGetMethod(method):

  def __init__(self, request, running, response = None):
    checks = [["param", "cId"], ["param", "mId"]]
    super(mediaLocationGetMethod, self).__init__(request, running, checks)
    self.response = response
    if not self.error:
      self.run()
    
  def run(self):
    self._log("locationGet")
    fmt = self.params.format if self.params.format in ["gpx", "kml"] else "gpx"
    chat = db.Chats.find_one({"_id": self.params.cId, "messages": {"$elemMatch": {"id": self.params.mId}}}, {"messages.$": 1})
    if chat:
      media = chat["messages"][0]["media"]
      caption = chat["messages"][0]["body"] if "body" in chat["messages"][0] else "Location"
      if self.response:
        self.response.set_header("Content-Type", "application/octet-stream; charset=UTF-8")
        self.response.set_header("Content-Disposition", "attachment; filename=%s.%s" % (urllib.quote_plus(caption.encode('utf8','replace')), fmt))
      if format == "kml":
        root = etree.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
        document = etree.Element("Document")
        placemark = etree.Element("Placemark")
        name = etree.Element("name")
        name.text = caption
        placemark.append(name)
        point = etree.Element("Point")
        coordinates = etree.Element("coordinates")
        coordinates.text = "%s,%s,0" % (media["latitude"], media["longitude"])
        point.append(coordinates)
        placemark.append(point)
        document.append(placemark)
        root.append(document)
      else:
        root = etree.Element("gpx", version="1.0")
        name = etree.Element("name")
        name.text = caption
        root.append(name)
        wpt = etree.Element("wpt", lat=media["latitude"], lon=media["longitude"])
        wpt_name = etree.Element("name")
        wpt_name.text = caption
        wpt.append(wpt_name)
        root.append(wpt)
      self.queue.put(etree.tostring(root, pretty_print = True, xml_declaration = True, encoding='UTF-8'))
      self.queue.put(StopIteration)
    else:
      self._die("file-not-found")
