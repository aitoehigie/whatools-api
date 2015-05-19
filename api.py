#!/usr/bin/python
#  -*- coding: utf8 -*-
import sys
from bottle import route, run, request, response, static_file, BaseRequest, FormsDict, error
from PIL import Image
from helpers import *
from events import *
from methods import *
from yowsup.layers.protocol_media.mediauploader import MediaUploader

reload(sys)
sys.setdefaultencoding('utf8')
BaseRequest.MEMFILE_MAX = 10 * 1024 * 1024 

@route("/message", method="POST")
def message_post():
  return messagePostMethod(request, running).queue

@route("/line/coderequest", method="GET")
def line_coderequest():
  return lineCodeRequestGetMethod(request, running).queue

@route("/line/regrequest", method="GET")
def line_regrequest():
  return lineRegRequestGetMethod(request, running).queue
  
@route("/subscribe", method="GET")
def subscribe():
  return subscribeGetMethod(request, running).queue
  
@route("/unsubscribe", method="GET")
def unsubscribe():
  return unsubscribeGetMethod(request, running).queue

@route("/history", method="GET")
def history():
  return historyGetMethod(request, running).queue
  
@route("/nickname", method="GET")
def nickname_get():
  return nicknameGetMethod(request, running).queue

@route("/nickname", method="POST")
def nickname_post():
  return nicknamePostMethod(request, running).queue

@route("/status", method="GET")
def status_get():
  return statusGetMethod(request, running).queue
  
@route("/status", method="POST")
def status_post():
  return statusPostMethod(request, running).queue

@route("/avatar", method="POST")
def avatar_post():
  return avatarPostMethod(request, running).queue
  
@route("/media/vcard", method="GET")
def media_vcard_get():
  return mediaVcardGetMethod(request, running, response = response).queue
    
@route("/media/vcard", method="POST")
def media_vCard_post():
  return mediaVcardPostMethod(request, running).queue
  
@route("/media/location", method="GET")
def media_location_get():
  return mediaLocationPostMethod(request, running, response = response).queue
    
@route("/media/picture", method="POST")
def media_picture_post():
  return mediaPicturePostMethod(request, running).queue
  
'''
STATIC CONTENT
'''
@route('/:filename#.*#')
def send_static(filename):
    return static_file(filename, './static/')
  
@route("/", method="GET")
def index():
  return static_file('index.html', './static')

def main():
  recover(list(db.Lines.find({"tokens.active": True, "api": v, "deleted": {"$in": [None, False]}}, {"tokens.$": 1})))
  run(host="127.0.0.1", port="8082", server='gevent')

if __name__ == "__main__":
  main()
