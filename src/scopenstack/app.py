"""
Initilize Flask App and logging

"""

import sys
import os

from flask import Flask
from flaskext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
if os.environ.has_key("SCOPENSTACK_SETTINGS"):
    app.config.from_envvar('SCOPENSTACK_SETTINGS')
db = SQLAlchemy(app)

import logging

logger = logging.getLogger('scopenstack')

if app.config.has_key('LOGGING_FILE'):
    handler = RotatingFileHandler(app.config['LOGGING_FILE'],
                                      maxBytes=10000000,
                                      backupCount=5)
else:
    handler = logging.StreamHandler(sys.stdout)

formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

if app.config.get('DEBUG', False):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
