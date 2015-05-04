from yowsup.structs import ProtocolEntity, ProtocolTreeNode
from .receipt import ReceiptProtocolEntity
class IncomingReceiptProtocolEntity(ReceiptProtocolEntity):

    '''
    delivered:
    <receipt to="xxxxxxxxxxx@s.whatsapp.net" id="1415389947-15"></receipt>

    read
    <receipt to="xxxxxxxxxxx@s.whatsapp.net" id="1415389947-15" type="read"></receipt>

    INCOMING
    <receipt offline="0" from="xxxxxxxxxx@s.whatsapp.net" id="1415577964-1" t="1415578027"></receipt>
    '''

    def __init__(self, _id, _from, timestamp, offline = None, type = None, ids = None):
        super(IncomingReceiptProtocolEntity, self).__init__(_id)
        self.setIncomingData(_from, timestamp, offline, type, ids)

    def setIncomingData(self, _from, timestamp, offline = None, type = None, ids = None):
        self._from = _from
        self.timestamp = timestamp
        self._type = type
        self.offline = offline == "1" or None
        self.ids = ids

    def toProtocolTreeNode(self):
        node = super(IncomingReceiptProtocolEntity, self).toProtocolTreeNode()
        node.setAttribute("from", self._from)
        node.setAttribute("t", str(self.timestamp))
        if self.offline is not None:
            node.setAttribute("offline", "1" if self.offline else "0")
        if self._type is not None:
            node.setAttribute("type", self._type)
        if self.ids is not None:
            items = []
            for idx in self.ids:
                items.append(ProtocolTreeNode("item", {"id": idx}))
            list_node = ProtocolTreeNode("list", None, items)
        return node

    def __str__(self):
        out = super(IncomingReceiptProtocolEntity, self).__str__()
        out += "From: %s\n" % self._from
        out += "Timestamp: %s\n" % self.timestamp
        if self.offline is not None:
            out += "Offline: %s\n" % ("1" if self.offline else "0")
        if self._type is not None:
            out += "Type: %s\n" % (self._type)
        if self.ids is not None:
            out += "Ids: ["
            for idx in self.ids:
                out += "%s, " % (idx)
            out += "]\n"
        return out

    @staticmethod
    def fromProtocolTreeNode(node):
        receipt_items = []
        list_node = node.getChild("list")
        if list_node is not None:
            for item_node in list_node.getAllChildren("item"):
                receipt_items.append(item_node.getAttributeValue("id"))
        return IncomingReceiptProtocolEntity(
            node.getAttributeValue("id"),
            node.getAttributeValue("from"),
            node.getAttributeValue("t"),
            node.getAttributeValue("offline"),
            node.getAttributeValue("type"),
            receipt_items
            )
