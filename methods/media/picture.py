from methods.method import method
from helpers import *
from bson import objectid
from yowsup.layers.protocol_media.mediauploader import MediaUploader
import os, time

class mediaPicturePostMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "expired", "token", ["permission", "write"], ["param", "to"], ["file", "attachment"], "inactive"]
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
    
    def success(resultEntity, requestEntity):
      self._log("mediaPicturePostProgress")
      
      def uploadSuccess(path, to, url):
        chat = db.Chats.find_one({"from": self.line["_id"], "to": to})
        if chat and not len(chat["messages"]):
          self.wa.call("presence_subscribe", [to])
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
        self.push("media_carbon", {"id": msgId, "to": to, "caption": caption, "timestamp": stamp, "broadcast": broadcast})
        self._success()
        
      def uploadError(path, to, url):
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
      
    def error(errorEntity, requestEntity):
      self._log("mediaPicturePostError")
      self._die("request-error")
    
    self.wa.call("media_upload_request", ["image", path, success, error])
