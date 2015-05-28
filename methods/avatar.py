from method import method
from helpers import *
from PIL import Image
import time

class avatarGetMethod(method):

  def __init__(self, request, running, response):
    checks = ["key", "line", "expired", "token", ["permission", "read"], ["param", "pn"], "inactive"]
    super(avatarGetMethod, self).__init__(request, running, checks)
    self.response = response
    if not self.error:
      self.run()
    
  def run(self):
    self._log("avatarGet")
    
    pn = self.params.pn if self.params.honor else phoneFormat(self.line["cc"], self.params.pn)
    
    def success(item):
      path = "%s%s" % (g.storage, item["src"])
      with open(path, 'rb') as f:
        if self.response:
          self.response.set_header("Content-Type", "image/jpg; charset=UTF-8")
          self.response.set_header("Content-Disposition", "attachment; filename=%s.jpg" % item["id"])
        self.queue.put(f.read())
        self.queue.put(StopIteration)
    
    avatar = db.Avatars.find_one({"jid": pn})
    
    if avatar:
      success(avatar["items"][0])
      
    else:
    
      def iqSuccess(resultIq, requestIq):
        name = "avatars/%s-%s.jpg" % (pn, resultIq.getPictureId())
        path = "%s%s" % (g.storage, name)
        resultIq.writeToFile(path)
        item = {"src": name, "id": resultIq.getPictureId()}
        db.Avatars.update({"jid": pn}, {"$push": {"items": item}}, True)
        success(item)
        
      def iqError(errorIq, requestIq):
        self._log("avatarGetError")
        self._die("item-not-found", 404)
        
      self.wa.call("profile_getPicture", [pn, iqSuccess, iqError])


class avatarPostMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "expired", "token", ["permission", "write"], ["param", "src"], "inactive"]
    super(avatarPostMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("avatarPost")
    
    def success(resultIq, requestIq):
      item = {"src": self.src, "id": resultIq.getPictureId()}
      db.Avatars.update({"jid": self.line["cc"] + self.line["pn"]}, {"$push": {"items": item}}, True)
      self._log("avatarPostSuccess")
      self._success()
      
    def fail(errorIq, requestIq):
      self._log("avatarPostError")
      self._die()
    
    src = self.params.src
    name = "avatars/%s%s-%s.jpg" % (self.line["cc"], self.line["pn"], str(int(time.time())))
    path = g.storage + name
    f = open(path, "wb")
    f.write(src.decode('base64'))
    f.close()
    src = Image.open(path)
    pictureData = bytearray(src.resize((640, 640)).tostring("jpeg", "RGB"))
    previewData = bytearray(src.resize((96, 96)).tostring("jpeg", "RGB"))
    idx = self.wa.call("profile_setPicture", [pictureData, previewData, success, fail])
    self.src = name
