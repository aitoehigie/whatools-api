from yowsup.common import YowConstants
from yowsup.layers                                     import YowLayerEvent
from yowsup.layers.interface                           import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.network                             import YowNetworkLayer
from yowsup.layers.auth                                import YowAuthenticationProtocolLayer
from yowsup.layers.protocol_acks.protocolentities      import *
from yowsup.layers.protocol_ib.protocolentities        import *
from yowsup.layers.protocol_iq.protocolentities        import *
from yowsup.layers.protocol_media.protocolentities     import *
from yowsup.layers.protocol_messages.protocolentities  import *
from yowsup.layers.protocol_presence.protocolentities  import *
from yowsup.layers.protocol_receipts.protocolentities  import *


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
    
    def normalizeData(self, data):
        for (i, item) in enumerate(data):
          if type(item) == str and len(item) > 255:
            data[i] = "[File]"
        return data

    def normalizeJid(self, number):
        if '@' in number:
            return number
        return "%s@s.whatsapp.net" % number

    def handle(self, event, data = {}):
        self.log(self.line["_id"], event, self.normalizeData(data[:]));
        if event in self.handlers:
            return self.handlers[event](self, *data)
        else:
            print("unhandled '%s' event" % event)
            return False
            
    methods = {}
    
    def logout(self):
        self.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))
    methods['logout'] = logout;
    
    def message_send(self, pn, body):
        outgoingMessage = TextMessageProtocolEntity(body, to=self.normalizeJid(pn))
        self.toLower(outgoingMessage)
        return outgoingMessage.getId()
    methods['message_send'] = message_send;
    
    def presence_sendAvailable(self, nickname):
        presence = PresenceProtocolEntity("available", nickname)
        self.toLower(presence)
    methods['presence_sendAvailable'] = presence_sendAvailable

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
        if entity.getType() == 'get':
            if entity.getXmlns() == 'urn:xmpp:ping':
              self.onPing(entity)

    @ProtocolEntityCallback("message")
    def onMessage(self, entity):
        if entity.getType() == 'text':
            self.onTextMessage(entity)
        elif entity.getType() == 'media':
            self.onMediaMessage(entity)
            
    @ProtocolEntityCallback("notification")
    def onNotification(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "notification", entity.getType())
        self.toLower(ack)
    
    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        idx = entity.getId()
        jid = entity.getFrom()
        grade = "visible" if entity.getType() else "delivered"
        if self.handle("onAck", [idx, jid, grade]):
          ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", "delivery")
          self.toLower(ack)

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
        self.cb("success", payload);
        
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
        if entity.isGroupMessage():
            '''if self.handle("onGroupMessageReceived", (idx, participant, jid, body, stamp, notify)):
                receipt = OutgoingReceiptProtocolEntity(idx, to)
                self.toLower(receipt)'''
            receipt = OutgoingReceiptProtocolEntity(idx, jid)
            self.toLower(receipt)
        else:
            if self.handle("onMessageReceived", [idx, jid, body, stamp, notify, broadcast]):
                receipt = OutgoingReceiptProtocolEntity(idx, jid)
                self.toLower(receipt) 

    def onMediaMessage(self, entity):
        idx = entity.getId()
        jid = entity.getFrom()
        broadcast = entity.isBroadcast()
        if entity.getMediaType() == "image":
            caption = entity.getCaption()
            preview = entity.getPreview()
            url = entity.getMediaUrl()
            size = entity.getMediaSize()
            receipt = OutgoingReceiptProtocolEntity(idx, jid)
            if self.handle("onMediaReceived", [idx, jid, caption, "image", preview, url, size, broadcast]):
                self.toLower(receipt)
        elif entity.getMediaType() == "audio":
            url = entity.getMediaUrl()
            size = entity.getMediaSize()
            receipt = OutgoingReceiptProtocolEntity(idx, jid)
            if self.handle("onMediaReceived", [idx, jid, None, "audio", None, url, size, broadcast]):
                self.toLower(receipt)
        elif entity.getMediaType() == "video":
            preview = entity.getPreview()
            url = entity.getMediaUrl()
            size = entity.getMediaSize()
            receipt = OutgoingReceiptProtocolEntity(idx, jid)
            if self.handle("onMediaReceived", [idx, jid, None, "video", preview, url, size, broadcast]):
                self.toLower(receipt)
        elif entity.getMediaType() == "location":
            preview = entity.getPreview()
            latitude = entity.getLatitude()
            longitude = entity.getLongitude()
            receipt = OutgoingReceiptProtocolEntity(entity.getId(), entity.getFrom())
            if self.handle("onMediaReceived", [idx, jid, None, "location", preview, latitude, longitude, broadcast]):
                self.toLower(receipt)
        elif entity.getMediaType() == "vcard":
            receipt = OutgoingReceiptProtocolEntity(entity.getId(), entity.getFrom())
            self.toLower(receipt)

