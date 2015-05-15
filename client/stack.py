from yowsup.stacks import YowStack, YOWSUP_CORE_LAYERS, YOWSUP_PROTOCOL_LAYERS_FULL
from .layer import AsyncLayer
from yowsup.layers import *
from yowsup.layers.auth                        import YowCryptLayer, YowAuthenticationProtocolLayer, AuthError
from yowsup.layers.coder                       import YowCoderLayer
from yowsup.layers.network                     import YowNetworkLayer
from yowsup.layers.protocol_messages           import YowMessagesProtocolLayer
from yowsup.layers.protocol_media              import YowMediaProtocolLayer
from yowsup.layers.stanzaregulator             import YowStanzaRegulator
from yowsup.layers.protocol_receipts           import YowReceiptProtocolLayer
from yowsup.layers.protocol_acks               import YowAckProtocolLayer
from yowsup.layers.logger                      import YowLoggerLayer
from yowsup.layers.axolotl                     import YowAxolotlLayer
from yowsup.common import YowConstants
from yowsup import env
import logging

logging.basicConfig(level=logging.DEBUG)

class YowsupAsyncStack(object):
    def __init__(self, line, token, eventHandlers, logger, cb):
        credentials = [line["cc"] + line["pn"], line["pass"]]
        layers = (
            AsyncLayer,
            YowParallelLayer(YOWSUP_PROTOCOL_LAYERS_FULL),
            YowLoggerLayer,
            YowAxolotlLayer,
            YowCoderLayer,
            YowCryptLayer,
            YowStanzaRegulator,
            YowNetworkLayer
        )
        self.stack = YowStack(layers)
        self.stack.setProp(AsyncLayer.LINE, line)
        self.stack.setProp(AsyncLayer.TOKEN, token)
        self.stack.setProp(AsyncLayer.HANDLERS, eventHandlers)
        self.stack.setProp(AsyncLayer.LOGGER, logger)
        self.stack.setProp(AsyncLayer.CB, cb)
        self.stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS, credentials)
        self.stack.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[0])
        self.stack.setProp(YowCoderLayer.PROP_DOMAIN, YowConstants.DOMAIN)
        self.stack.setProp(YowCoderLayer.PROP_RESOURCE, env.CURRENT_ENV.getResource())
        self.layer = self.stack.getLayer(7)

    def login(self):
        self.layer.init()
        self.stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
        try:
            self.stack.loop()
        except AuthError as e:
             self.stack.getProp(AsyncLayer.CB)(self, False)
            
    def logout(self):
        return self.call("logout", [])
            
    def call(self, method, params, success = None, fail = None):
        return self.layer.call(method, params, success, fail)
