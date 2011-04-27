"""
Test suite for OpenStack SpotCloud adapter

"""

import unittest
import json
import sys

import uuid

from flask import request

from scopenstack.app import app, db
from scopenstack.models import VM, Package, HardwareTemplate, Task
from scopenstack import auth
from scopenstack.api import rest, ptemplate_list

import logging

logger = logging.getLogger('scopenstack')
logger.setLevel(logging.WARNING)

USER = 'spotcloud'
PASSWD = 'password'

def get_auth_args():
    "Get query string with auth digest for GET"
    return "ecp_username=%s&ecp_auth_digest=%s" % (
        USER,
        auth.get_digest(PASSWD, {'ecp_username': USER}))


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
        app.config['SPOTCLOUD_USER'] = 'spotcloud'
        app.config['SPOTCLOUD_PASSWD'] = 'password'
        db.drop_all()
        db.create_all()
        self.app = app.test_client()

        pkg_uuid = str(uuid.uuid1())
        self.pkg = Package(ecp_uuid=pkg_uuid,
                      nova_id='dummy_nova_id',
                      state='ready')
        db.session.add(self.pkg)
        db.session.commit() 
   
        hardware_uuid = str(uuid.uuid1())
        self.hardware = HardwareTemplate(
            ecp_uuid=hardware_uuid,
            name='test',
            nova_id='dummy_nova_id',
            cpus=2,
            arch='i386',
            memory=8000)
        db.session.add(self.hardware)
        db.session.commit()

    def tearDown(self):
        db.drop_all()

    def test_digest(self):
        self.assertTrue(
            '2GNfPPMxfosE5u4AOY7mRAawMp8=' == \
                auth.get_digest('password', {'ecp_username':'spotcloud'}))

    def test_package1(self):
        pkg2 = Package.query.all()[0]
        self.assertTrue(self.pkg.ecp_uuid == pkg2.ecp_uuid)


    def test_hardware(self):
        response = self.app.get(
            "/rest/hosting/htemplate/list?%s" % get_auth_args())
        data = json.loads(response.data)
        if data['errno'] != 0:
            raise RuntimeError(data['message'])
        self.assertTrue(
            data['templates'][0]['uuid'] == self.hardware.ecp_uuid)


    def test_package2(self):
        response = self.app.get(
            "/rest/hosting/ptemplate/list?%s" % get_auth_args())
        data = json.loads(response.data)
        if data['errno'] != 0:
            raise RuntimeError(data['message'])
        self.assertTrue(
            data['packages'][0]['uuid'] == self.pkg.ecp_uuid)

if __name__ == '__main__':
    unittest.main()
