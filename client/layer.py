from yowsup.common import YowConstants
from yowsup.structs.protocoltreenode                   import ProtocolTreeNode
from yowsup.layers                                     import YowLayerEvent
from yowsup.layers.interface                           import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.network                             import YowNetworkLayer
from yowsup.layers.auth                                import YowAuthenticationProtocolLayer
from yowsup.layers.axolotl                             import YowAxolotlLayer
from yowsup.layers.protocol_acks.protocolentities      import *
from yowsup.layers.protocol_contacts.protocolentities  import *
from yowsup.layers.protocol_ib.protocolentities        import *
from yowsup.layers.protocol_iq.protocolentities        import *
from yowsup.layers.protocol_media.protocolentities     import *
from yowsup.layers.protocol_messages.protocolentities  import *
from yowsup.layers.protocol_notifications.protocolentities  import *
from yowsup.layers.protocol_presence.protocolentities  import *
from yowsup.layers.protocol_profiles.protocolentities  import *
from yowsup.layers.protocol_receipts.protocolentities  import *
from yowsup.layers.protocol_calls.protocolentities     import *
import time

class AsyncLayer(YowInterfaceLayer):

    LINE = "com.waalt.whatools.prop.line"
    TOKEN = "com.waalt.whatools.prop.token"
    HANDLERS = "com.waalt.whatools.prop.handlers"
    LOGGER = "com.waalt.whatools.prop.logger"
    CB = "com.waalt.whatools.prop.cb"
    
    def init(self):
        self.line = self.getProp(self.__class__.LINE)
        self.token = self.getProp(self.__class__.TOKEN)
        self.handlers = self.getProp(self.__class__.HANDLERS)
        self.log = self.getProp(self.__class__.LOGGER)
        self.cb = self.getProp(self.__class__.CB)
        
    def onEvent(self, layerEvent):
        print("$$$$ '%s'" % layerEvent.getName())
        if layerEvent.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
            self.handle("onDisconnected", [layerEvent.getArg("reason")])
        elif layerEvent.getName() == YowAuthenticationProtocolLayer.EVENT_AUTHED:
            self.handle("onAuthSuccess")
    
    def normalizeData(self, data):
        data = list(data)
        for (i, item) in enumerate(data):
          if type(item) == str and len(item) > 255:
            data[i] = "[File]"
        return tuple(data)

    def normalizeJid(self, number):
        if '@' in number:
            jid = number
        elif '-' in number:
            jid = "%s@g.us" % number
        else:
            jid = "%s@s.whatsapp.net" % number
        return jid

    def handle(self, event, data = []):
        self.log(self.line["_id"], event, self.normalizeData(data[:]));
        if event in self.handlers:
            return self.handlers[event](self, *data)
        else:
            print("unhandled '%s' event" % event)
            return False
            
    methods = {}

    def contact_sync(self, numbers, mode, context, success, error):
        def iqSuccess(resultEntity, requestEntity):
          success(resultEntity.inNumbers, resultEntity.outNumbers, resultEntity.invalidNumbers)
        iq = GetSyncIqProtocolEntity(numbers, mode, context)
        self._sendIq(iq, iqSuccess, error)
        return iq.getId()
    methods['contact_sync'] = contact_sync
    
    def logout(self):
        self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
    methods['logout'] = logout;

    def media_send(self, type, path, to, url, ip = None, caption = None):
        media = {"type": type}
        to = self.normalizeJid(to)
        if type in ["image"]:
          if type == "image":
            entity = ImageDownloadableMediaMessageProtocolEntity.fromFilePath(path, url, ip, to, caption = caption)
            media["preview"] = entity.getPreview()
          media["size"] = entity.getMediaSize()
          media["url"] = entity.getMediaUrl()
          media["idx"] = entity.getId()
          self.toLower(entity)
          return media
        else:
          return False
    methods['media_send'] = media_send

    def media_upload_request(self, type, path, success, error):
        entity = RequestUploadIqProtocolEntity(type, filePath=path)
        self._sendIq(entity, success, error)
        return entity.getId()
    methods['media_upload_request'] = media_upload_request

    def media_vcard_send(self, name, card_data, to):
        media = VCardMediaMessageProtocolEntity(name, card_data, to="%s@s.whatsapp.net" % to)
        self.toLower(media)
        return media.getId()
    methods['media_vcard_send'] = media_vcard_send

    def message_send(self, pn, body):
        outgoingMessage = TextMessageProtocolEntity(body, to=self.normalizeJid(pn))
        self.toLower(outgoingMessage)
        return outgoingMessage.getId()
    methods['message_send'] = message_send
    
    def presence_sendAvailable(self, nickname):
        presence = PresenceProtocolEntity("available", nickname)
        self.toLower(presence)
    methods['presence_sendAvailable'] = presence_sendAvailable
    
    def presence_subscribe(self, to):
        presence = SubscribePresenceProtocolEntity(self.normalizeJid(to))
        self.toLower(presence)
        return True
    methods['presence_subscribe'] = presence_subscribe
    
    def presence_unsubscribe(self, to):
        presence = UnsubscribePresenceProtocolEntity(self.normalizeJid(to))
        self.toLower(presence)
        return True
    methods['presence_unsubscribe'] = presence_unsubscribe

    def profile_getPicture(self, pn, success, error):
        iq = GetPictureIqProtocolEntity(self.normalizeJid(pn))
        self._sendIq(iq, success, error)
        return iq.getId()
    methods['profile_getPicture'] = profile_getPicture
    
    def profile_setPicture(self, pictureData, previewData, success, error):
        iq = SetPictureIqProtocolEntity(self.normalizeJid("%s%s" % (self.line["cc"], self.line["pn"])), previewData, pictureData)
        self._sendIq(iq, success, error)
        return iq.getId()
    methods['profile_setPicture'] = profile_setPicture
    
    def profile_setStatus(self, status, success, error):
        iq = SetStatusIqProtocolEntity(status)
        self._sendIq(iq, success, error)
        return iq.getId()
    methods['profile_setStatus'] = profile_setStatus

    def call(self, method, params):
        if method in self.methods:
            return self.methods[method](self, *params)
        else:
            print("unsupported '%s' method" % method)
    
    @ProtocolEntityCallback("ib")
    def onIb(self, entity):
        if isinstance(entity, DirtyIbProtocolEntity):
          iq = CleanIqProtocolEntity("groups", YowConstants.DOMAIN)
          self.toLower(iq)
            
    @ProtocolEntityCallback("iq")
    def onIq(self, entity):
        if entity.getType() == "get":
            if entity.getXmlns() == "urn:xmpp:ping":
              self.onPing(entity)
        elif entity.getType() == "result":
            self.onResult(entity)

    @ProtocolEntityCallback("message")
    def onMessage(self, entity):
        if entity.getType() == 'text':
            self.onTextMessage(entity)
        elif entity.getType() == 'media':
            self.onMediaMessage(entity)
            
    @ProtocolEntityCallback("notification")
    def onNotification(self, entity):
        type = entity.getType()
        if isinstance(entity, SetPictureNotificationProtocolEntity):
            self.handle("onNotificationSetPicture", [entity.getFrom(), entity.setJid, entity.setId])
        elif isinstance(entity, DeletePictureNotificationProtocolEntity):
            self.handle("onNotificationDeletePicture", [entity.getFrom(), entity.deleteJid])
    
    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        idx = entity.getId()
        jid = entity.getFrom()
        type = entity.getType()
        grade = {
          "read": "visible",
          "error": "error"
        }.get(type, "delivered")
        if self.handle("onAck", [idx, jid, grade]):
            ack = OutgoingAckProtocolEntity(idx, "receipt", type or "delivery", jid)
            self.toLower(ack)
            '''if len(entity.ids):
                for idx in entity.ids:
                    ack = OutgoingAckProtocolEntity(idx, "receipt", type or "delivery", jid)
                    self.toLower(ack)'''

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        payload = {
          "status": entity.status,
          "kind": entity.kind,
          "creation": entity.creation,
          "expiration": entity.expiration,
          "props": entity.props,
          "t": entity.t
        }
        self.cb(self, "success", payload);
        
    @ProtocolEntityCallback("call")
    def onCall(self, entity):
        if entity.getType() == "offer":
          call = CallProtocolEntity(None, "reject", int(time.time()), _to = entity.getFrom(), callId = entity.getCallId())
          self.toLower(call)
          
    @ProtocolEntityCallback("presence")
    def onPresence(self, entity):
        self.handle("onPresence", [entity.getType(), entity.getFrom(), entity.getLast()])
        
    def onPing(self,entity):
        idx = entity.getId()
        jid = entity.getFrom()
        iq = PongResultIqProtocolEntity(jid, idx)
        self.toLower(iq)
        self.handle("onPing", [idx])

    def onTextMessage(self,entity):
        idx = entity.getId()
        jid = entity.getFrom()
        participant = entity.getParticipant()
        body = entity.getBody()
        stamp = entity.getTimestamp()
        notify = entity.getNotify()
        broadcast = entity.isBroadcast()
        if self.handle("onMessageReceived", (idx, jid, participant, body, stamp, notify, broadcast)):
            receipt = OutgoingReceiptProtocolEntity(idx, jid)
            self.toLower(receipt)

    def onMediaMessage(self, entity):
        idx = entity.getId()
        jid = entity.getFrom()
        broadcast = entity.isBroadcast()
        participant = entity.getParticipant()
        notify = entity.getNotify()
        if entity.getMediaType() == "image":
            caption = entity.getCaption()
            preview = entity.getPreview()
            url = entity.getMediaUrl()
            size = entity.getMediaSize()
            receipt = OutgoingReceiptProtocolEntity(idx, jid)
            if self.handle("onMediaReceived", [idx, jid, participant, caption, "image", preview, url, size, notify, broadcast]):
                self.toLower(receipt)
        elif entity.getMediaType() == "audio":
            url = entity.getMediaUrl()
            size = entity.getMediaSize()
            receipt = OutgoingReceiptProtocolEntity(idx, jid)
            if self.handle("onMediaReceived", [idx, jid, participant, None, "audio", None, url, size, notify, broadcast]):
                self.toLower(receipt)
        elif entity.getMediaType() == "video":
            preview = entity.getPreview()
            url = entity.getMediaUrl()
            size = entity.getMediaSize()
            receipt = OutgoingReceiptProtocolEntity(idx, jid)
            if self.handle("onMediaReceived", [idx, jid, participant, None, "video", preview, url, size, notify, broadcast]):
                self.toLower(receipt)
        elif entity.getMediaType() == "location":
            preview = entity.getPreview()
            latitude = entity.getLatitude()
            longitude = entity.getLongitude()
            name = entity.getLocationName()
            receipt = OutgoingReceiptProtocolEntity(entity.getId(), entity.getFrom())
            if self.handle("onMediaReceived", [idx, jid, participant, name, "location", preview, latitude, longitude, notify, broadcast]):
                self.toLower(receipt)
        elif entity.getMediaType() == "vcard":
            caption = entity.getName()
            card_data = entity.getCardData()
            receipt = OutgoingReceiptProtocolEntity(entity.getId(), entity.getFrom())
            if self.handle("onMediaReceived", [idx, jid, participant, caption, "vcard", card_data, None, None, notify, broadcast]):            
                self.toLower(receipt)

    def onResult(self, entity):
        idx = entity.getId()
        pass
