from methods.method import method
from helpers import *
from bson import objectid
from yowsup.layers.protocol_media.mediauploader import MediaUploader
import os, time

class mediaPicturePostMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "expired", "token", ["permission", "write"], ["param", "to"], ["file", "attachment"], "active"]
    super(mediaPicturePostMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("mediaPicturePost")
    caption = self.params.caption.encode("utf-8", "replace").strip()
    upload = self.request.files.get("attachment")
    to = self.params.to
    honor = self.params.honor
    broadcast = self.params.broadcast
    if not honor:
      to = phoneFormat(self.line["cc"], to)
    jid = self.wa.normalizeJid(to)
    folder =  "%stemp/%s" % (g.storage, to)
    path = "%s/%s" % (folder, upload.filename)
    if not os.path.exists(folder):
      os.makedirs(folder)
    content = upload.file.read()
    if "Content-Encoding" in self.request.headers:
      if self.request.headers["Content-Encoding"] == "base64":
        content = content.decode("base64")
      else:
        self._die("wrong-encoding")
    with open(path, 'w') as open_file:
      open_file.write(content)
    chat = db.Chats.find_one({"from": self.line["_id"], "to": to})
      
    def success(inNumbers = [], outNumbers = [], invalidNumbers = []):
      if jid in inNumbers.values():   
        def urSuccess(resultEntity, requestEntity):
          self._log("mediaPicturePostProgress")
          
          def uploadSuccess(path, to, url):
            self._success()
            media = self.wa.call("media_send", ["image", path, to, url, caption])
            stamp = int(time.time() * 1000)
            media["preview"] = media["preview"].encode("base64") if "preview" in media else None
            msgId = media["idx"]
            del media["idx"]
            msg = {"id": msgId, "mine": True, "body": caption, "stamp": stamp, "ack": "sent", "media": media}
            if chat:
              db.Chats.update({"from": self.line["_id"], "to": to}, {"$push": {"messages": msg}, "$set": {"lastStamp": stamp, "unread": 0}});
            else:
              db.Chats.insert({"_id": str(objectid.ObjectId()), "from": self.line["_id"], "to": to, "messages": [msg], "lastStamp": stamp})
              self.wa.call("presence_subscribe", [to])
            self.push("media_carbon", {"id": msgId, "to": to, "caption": caption, "timestamp": stamp, "broadcast": broadcast})
            os.remove(path)
            
          def uploadError(path, to = None, url = None):
            self._log("mediaPicturePostError")
            self._die("upload-error")
            os.remove(path)
            
          def uploadProgress(path, to, url, progress):
            if not progress % 10:
              self._log("mediaPicturePostProgress", {"progress": progress})
              
          if resultEntity.isDuplicate():
            uploadSuccess(path, to, resultEntity.getUrl())
          else:
            mediaUploader = MediaUploader(to, phoneFormat(self.line["cc"], self.line["pn"]), path, 
                              resultEntity.getUrl(), resultEntity.getResumeOffset(),
                              uploadSuccess, uploadError, uploadProgress, async=False)
            mediaUploader.start()
          
        def urError(errorEntity, requestEntity):
          self._log("mediaPicturePostError")
          self._die("request-error")
        
        self.wa.call("media_upload_request", ["image", path, urSuccess, urError])

      elif jid in outNumbers.values():
        self._log("mediaPicturePostError")
        self._die("phone-number-not-in-whatsapp", 404)
      else:
        self._log("mediaPicturePostError")
        self._die("malformed-phone-number", 400)
    
    def error(errorEntity, requestEntity):
      self._log("mediaPicturePostError")
      self._die("request-error", 400)
    
    if chat and len(chat["messages"]):
      success({"0": jid})
    else:
      self.wa.call("contact_sync", [["+" + to], "delta", "interactive", success, error])
