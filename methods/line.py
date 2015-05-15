from method import method
from helpers import db
from yowsup.registration import *
import time

class lineCodeRequestGetMethod(method):

  def __init__(self, request, running):
    checks = ["user", ["param", "pn"], ["param", "cc"]]
    super(lineCodeRequestGetMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    wa = WACodeRequest(self.params.cc, self.params.pn, method = self.params.method)
    if wa:
      self._success(wa.send())
    else:
      self._die("could-not-send")


class lineRegRequestGetMethod(method):

  def __init__(self, request, running):
    checks = ["user", ["param", "pn"], ["param", "cc"], ["param", "code"]]
    super(lineRegRequestGetMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    wa = WACodeRequest(self.params.cc, self.params.pn, method = self.params.code)
    if wa:
      self._success(wa.register())
    else:
      self._die("could-not-register")
