from onAck import *
from onAuth import *
from onAxolotl import *
from onMedia import *
from onMessage import *
from onPresence import *
from onPing import *
from onNotification import *

eventHandler = {
  "onAck": onAck,
  "onAuthFailed": onAuthFailed,
  "onAuthSuccess": onAuthSuccess,
  "onAxolotlReady": onAxolotlReady,
  "onDisconnected": onDisconnected,
  "onMediaReceived": onMediaReceived,
  "onMessageReceived": onMessageReceived,
  "onNotificationDeletePicture": onNotificationDeletePicture,
  "onNotificationSetPicture": onNotificationSetPicture,
  "onPing": onPing,
  "onPresence": onPresence
}
