from method import method
from yowsup.common.constants import YowConstants
import shutil

class axolotlRegenGetMethod(method):

  def __init__(self, request, running):
    checks = ["key", "line", "expired", "token", ["permission", "write"], "inactive"]
    super(subscribeGetMethod, self).__init__(request, running, checks)
    if not self.error:
      self.run()
    
  def run(self):
    self._log("axolotlRegenGet")
    
    try:
      shutil.rmtree("%s/%s%s/" % (YowConstants.PATH_STORAGE, self.line["cc"], self.line["pn"]))
      self._success()

    except Exception as e:
      self._die("could-not-regenerate-keys", 500)
