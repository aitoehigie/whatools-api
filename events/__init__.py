from onAck import *
from onAuth import *
from onAxolotl import *
from onMedia import *
from onMessage import *
from onPresence import *
from onProfile import *
from onPing import *

eventHandler = {
  "onAck": onAck,
  "onAuthFailed": onAuthFailed,
  "onAuthSuccess": onAuthSuccess,
  "onAxolotlReady": onAxolotlReady,
  "onDisconnected": onDisconnected,
  "onMediaReceived": onMediaReceived,
  "onMessageReceived": onMessageReceived,
  "onPing": onPing,
  "onPresence": onPresence,
#  "onProfileSetPictureError": onProfileSetPictureError,
#  "onProfileSetPictureSuccess": onProfileSetPictureSuccess,
#  "onProfileSetStatusSuccess": onProfileSetStatusSuccess
}
