from yowsup.structs import ProtocolEntity, ProtocolTreeNode
from .ack import AckProtocolEntity
import time
class OutgoingAckProtocolEntity(AckProtocolEntity):

    '''
    <ack type="{{delivery | ?}}" class="{{message | receipt | ?}}" id="{{MESSAGE_ID}}">
    </ack>
    '''

    def __init__(self, _id, _class, _type, _to = None):
        super(OutgoingAckProtocolEntity, self).__init__(_id, _class)
        self.setOutgoingData(_type, _to)

    def setOutgoingData(self, _type, _to, _t = None):
        self._type = _type
        self._to = _to
        self._t = _t or str(int(time.time()))
    
    def toProtocolTreeNode(self):
        node = super(OutgoingAckProtocolEntity, self).toProtocolTreeNode()
        if self._type is not None:
            node.setAttribute("type", self._type)
        if self._to is not None:
            node.setAttribute("to", self._to)
        if self._t is not None:
            pass#node.setAttribute("t", self._t)
        return node

    def __str__(self):
        out  = super(OutgoingAckProtocolEntity, self).__str__()
        if self._node is not None:
            out += "Type: %s\n" % self._type
        return out

    @staticmethod
    def fromProtocolTreeNode(node):
        entity = AckProtocolEntity.fromProtocolTreeNode(node)
        entity.__class__ = OutgoingAckProtocolEntity
        entity.setOutgoingData(
            node.getAttributeValue("type"),
            node.getAttributeValue("to"),
            node.getAttributeValue("t")
        )
        return entity
