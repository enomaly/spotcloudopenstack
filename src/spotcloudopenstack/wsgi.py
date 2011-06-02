"""
Used to run from any uwsgi server or container

"""

from spotcloudopenstack.app import app as application
from spotcloudopenstack.api import rest
