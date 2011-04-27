"""
Run App
"""


from flask import request

from scopenstack.app import app, db
from scopenstack.novaconn import get_nova_connection, nova_manage
from scopenstack.models import HardwareTemplate, Package, VM, Task
from scopenstack.provision import ProvisionWorker
from scopenstack.api import rest

import logging
logger = logging.getLogger('scopenstack')


def main():
    "Run Flask application"
    logger.info("App started")
    app.run(host=app.config.get('HOST', "127.0.0.1"),
            port=app.config.get('PORT', 8080),
            debug=app.config.get("DEBUG", False))
    logger.info("App stopped")


if __name__ == '__main__':
    main()
