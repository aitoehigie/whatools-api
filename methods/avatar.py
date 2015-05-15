from method import method
from helpers import db
from PIL import Image
import time

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
    path = storage + name
    f = open(path, "wb")
    f.write(src.decode('base64'))
    f.close()
    src = Image.open(path)
    pictureData = bytearray(src.resize((640, 640)).tostring("jpeg", "RGB"))
    previewData = bytearray(src.resize((96, 96)).tostring("jpeg", "RGB"))
    idx = wa.call("profile_setPicture", [pictureData, previewData, success, fail])
    self.src = name
