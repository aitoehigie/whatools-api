import unittest
try:
    import Queue
except ImportError:
    import queue as Queue

class YowLayerEvent:
    def __init__(self, name, **kwargs):
        self.name = name
        self.detached = False
        if "detached" in kwargs:
            del kwargs["detached"]
            self.detached = True
        self.args = kwargs

    def isDetached(self):
        return self.detached

    def getName(self):
        return self.name

    def getArg(self, name):
        return self.args[name] if name in self.args else None


class YowLayer(object):
    __upper = None
    __lower = None
    _props = {}
    __detachedQueue = Queue.Queue()
    # def __init__(self, upperLayer, lowerLayer):
    #     self.setLayers(upperLayer, lowerLayer)

    def __init__(self):
        self.setLayers(None, None)

    def setStack(self, stack):
        self.__stack = stack

    def getStack(self):
        return self.__stack

    def setLayers(self, upper, lower):
        self.__upper = upper
        self.__lower = lower

    def send(self, data):
        self.toLower(data)

    def receive(self, data):
        self.toUpper(data)

    def toUpper(self, data):
        if self.__upper:
            self.__upper.receive(data)

    def toLower(self, data):
        if self.__lower:
            self.__lower.send(data)

    def emitEvent(self, yowLayerEvent):
        if self.__upper and not self.__upper.onEvent(yowLayerEvent):
            if yowLayerEvent.isDetached():
                yowLayerEvent.detached = False
                self.getStack().execDetached(lambda :  self.__upper.emitEvent(yowLayerEvent))

            else:
                self.__upper.emitEvent(yowLayerEvent)


    def broadcastEvent(self, yowLayerEvent):
        if self.__lower and not self.__lower.onEvent(yowLayerEvent):
            if yowLayerEvent.isDetached():
                yowLayerEvent.detached = False
                self.getStack().execDetached(lambda:self.__lower.broadcastEvent(yowLayerEvent))
            else:
                self.__lower.broadcastEvent(yowLayerEvent)

    '''return true to stop propagating the event'''
    def onEvent(self, yowLayerEvent):
        return False

    def getProp(self, key, default = None):
        return self.getStack().getProp(key, default)

    def setProp(self, key, val):
        return self.getStack().setProp(key, val)


class YowProtocolLayer(YowLayer):
    def __init__(self, handleMap = None):
        super(YowProtocolLayer, self).__init__()
        self.handleMap = handleMap or {}
        self.iqRegistry = {}

    def receive(self, node):
        if not self.processIqRegistry(node):
            if node.tag in self.handleMap:
                recv, _ = self.handleMap[node.tag]
                if recv:
                    recv(node)

    def send(self, entity):
        if entity.getTag() in self.handleMap:
            _, send = self.handleMap[entity.getTag()]
            if send:
                send(entity)

    def entityToLower(self, entity):
        #super(YowProtocolLayer, self).toLower(entity.toProtocolTreeNode())
        self.toLower(entity.toProtocolTreeNode())

    def isGroupJid(self, jid):
        return "-" in jid

    def raiseErrorForNode(self, node):
        #logger.warn("Unimplemented notification type %s " % node)
        pass


    def _sendIq(self, iqEntity, onSuccess = None, onError = None):
        self.iqRegistry[iqEntity.getId()] = (iqEntity, onSuccess, onError)
        self.toLower(iqEntity.toProtocolTreeNode())

    def processIqRegistry(self, protocolTreeNode):
        if protocolTreeNode.tag == "iq":
            iq_id = protocolTreeNode["id"]
            if iq_id in self.iqRegistry:
                originalIq, successClbk, errorClbk = self.iqRegistry[iq_id]
                del self.iqRegistry[iq_id]

                if protocolTreeNode["type"] == "result" and successClbk:
                    successClbk(protocolTreeNode, originalIq)
                elif protocolTreeNode["type"] == "error" and errorClbk:
                    errorClbk(protocolTreeNode, originalIq)
                return True

        return False

class YowParallelLayer(YowLayer):
    def __init__(self, sublayers = None):
        super(YowParallelLayer, self).__init__()
        self.sublayers = sublayers or []
        self.sublayers = tuple([sublayer() for sublayer in sublayers])
        for s in self.sublayers:
            #s.setLayers(self, self)
            s.toLower = self.toLower
            s.toUpper = self.toUpper
            s.broadcastEvent = self.subBroadcastEvent
            s.emitEvent = self.subEmitEvent


    def setStack(self, stack):
        super(YowParallelLayer, self).setStack(stack)
        for s in self.sublayers:
            s.setStack(self.getStack())


    def receive(self, data):
        for s in self.sublayers:
            s.receive(data)

    def send(self, data):
        for s in self.sublayers:
            s.send(data)

    def subBroadcastEvent(self, yowLayerEvent):
        self.onEvent(yowLayerEvent)
        self.broadcastEvent(yowLayerEvent)

    def subEmitEvent(self, yowLayerEvent):
        self.onEvent(yowLayerEvent)
        self.emitEvent(yowLayerEvent)


    def onEvent(self, yowLayerEvent):
        stopEvent = False
        for s in self.sublayers:
            stopEvent = stopEvent or s.onEvent(yowLayerEvent)

        return stopEvent

    def __str__(self):
        return " - ".join([l.__str__() for l in self.sublayers])


class YowLayerTest(unittest.TestCase):
    def __init__(self, *args):
        super(YowLayerTest, self).__init__(*args)
        self.upperSink = []
        self.lowerSink = []
        self.toUpper = self.receiveOverrider
        self.toLower = self.sendOverrider

    def receiveOverrider(self, data):
        self.upperSink.append(data)

    def sendOverrider(self, data):
        self.lowerSink.append(data)

class YowProtocolLayerTest(YowLayerTest):
    def assertSent(self, entity):
        self.send(entity)
        try:
            self.assertEqual(entity.toProtocolTreeNode(), self.lowerSink.pop())
        except IndexError:
            raise AssertionError("Entity '%s' was not sent through this layer" % (entity.getTag()))

    def assertReceived(self, entity):
        node = entity.toProtocolTreeNode()
        self.receive(node)
        try:
            self.assertEqual(node, self.upperSink.pop().toProtocolTreeNode())
        except IndexError:
            raise AssertionError("'%s' was not received through this layer" % (entity.getTag()))
