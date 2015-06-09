#!/usr/bin/env python
from __init__ import *
from setuptools import setup, find_packages

__version__ = "2.0"

setup(name='whatools-api',
      version='2.0',
      description='Whatools WhatsApp API',
      author='Waaltcom',
      author_email='info@waalt.com',
      url='https://api.wha.tools/v2',
      py_modules = ['helpers.bot'],
      install_requires=['python-dateutil', 'argparse', 'python-axolotl>=0.1.7', 'pillow', 'bottle', 'gevent', 'httplib2', 'urllib3', 'pymongo', 'phonenumbers', 'lxml'],
     )
