#!/usr/bin/python
#  -*- coding: utf8 -*-
import re

ops = {
  'or': lambda a, b: a or b,
  'and': lambda a, b: a and b,
  'xor': lambda a, b: a ^ b
}

verbs = {
  'yes': lambda subj, obj: True,
  'exists': lambda subj, obj: subj is not None,
  'is': lambda subj, obj: str(subj) == str(obj),
  'starts': lambda subj, obj: re.compile('^%s' % str(obj)).match(str(subj)),
  'ends': lambda subj, obj: re.compile('%s$' % str(obj)).match(str(subj)),
  'contains': lambda subj, obj: re.compile(str(obj)).match(str(subj)),
  'lt': lambda subj, obj: subj < obj,
  'gt': lambda subj, obj: subj > obj
}

def evaluate(msg, conditions):
  return reduce(lambda prev, cur: ops[cur["op"]](prev, cur["sign"] == (cur["verb"] in verbs and cur["subj"] in msg and verbs[cur["verb"]](msg[cur["subj"]], cur["obj"]))), conditions, 0)

def run(message, conditions, consequences, actions):
  if conditions == False or evaluate(message, conditions):
    for consequence in consequences:
      actions[consequence["action"]](message, consequence[consequence["action"]])
