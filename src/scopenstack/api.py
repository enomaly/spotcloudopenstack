"""
Set of HTTP API calls for SpotCloud

"""

import json
import urllib
import re
import cgi


from flask import request, jsonify, abort

from scopenstack.app import app, db
from scopenstack.models import HardwareTemplate, VM, Task, Package
from scopenstack.provision import ProvisionWorker
from scopenstack.novaconn import get_nova_connection
from scopenstack.auth import check_auth, WrongAuth

import logging
logger = logging.getLogger('scopenstack')


@app.route("/rest/hosting/<path:path>",
           methods = ["GET", "PUT", "POST", "DELETE"])
def rest(path):
    """ Dispatcher method was created as workoround,
    but now used for central auth chek then 
    dispatching to the particular api methods.
    It could be removed in future.

    """
    if '?' in path:
        path = path.split('?')[0]

    logger.debug("Got %s to %s" % (
            request.method, path))
    try:
        check_auth()
        logger.debug("Auth OK")
    except WrongAuth, e:
        logger.warning(str(e))
        return jsonify(
            errno=1,
            message="Wrong digest auth: %s" % str(e))

        
    url2method = {
        'htemplate/list': htemplate_list,
        'utilization': utilization,
        'ptemplate/list': ptemplate_list,
        'network/list': network_list,
        'vm/list': vm_list,
        'vm': vm_put
       }

    view = url2method.get(path)
    if view:
        return view()
    
    match = re.search(
        'vm/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/?', 
        path)
    if match:
        return vm_uuid(match.group(1))
    
    abort(404)


def htemplate_list():
    "Return list of HardwareTemplates"
    return jsonify(
        errno=0,
        message='Success',
        templates=[
            x.to_dict() for x in HardwareTemplate.query.all()])
    

def utilization():
    "Just dummy method for now"
    return jsonify(
        total_memory=8000,
        free_storage=800000,
        committed_storage=800000,
        free_memory=6000,
        total_storage=800000,
        loadone=0.1,
        loadfive=0.1,
        loadfifteen=0.1,
        cpus=4)


def ptemplate_list():
    "Return list of Packages"
    return jsonify(
            errno=0,
            message='Success',
            packages=[
                x.to_dict() for x in Package.query.all()])


def network_list():
    """This method exists only for SpotCloud 
    backward compatibility. The network info came back
    to vm_put method never used.

    """
    return jsonify(
        errno=0,
        message="Success",
        networks=[
            {'uuid': '69aeeed3-f2aa-41c4-8d3a-a264413aa52a',
             'name': 'Spot Cloud',
             'interface_name': None,
             'vlan_id': None}])


def vm_list():
    "Return list of VMs"
    VM.sync_with_nova()
    return jsonify(
        errno=0,
        message="Success",
        vms=[x.to_dict() for x in VM.query.all()])



def vm_uuid(vm_uuid):
    """Return dict on GET, delete on DELETE and
    delete on POST with action=delete

    """

    vm = VM.query.get(vm_uuid)
    if not vm:
        abort(404)

    if request.method == 'GET':
        return json.dumps(
            dict(
                errno=0,
                message='Success',
                vm=vm.to_dict()))

    action_delete = request.method == 'POST' and request.form.get(
        'action') == 'delete'

    if request.method == 'DELETE' or action_delete:
        conn = get_nova_connection()
        conn.terminate_instances([vm.nova_id])
        db.session.delete(vm)
        db.session.commit()
        msg = "VM %s was deleted" % vm_uuid
        logger.debug(msg)
        return json.dumps(
            dict(
                errno=0,
                message=msg))
    
    return json.dumps(
        dict(
            errno=1,
            message="This action is not supported"))


def vm_put():
    "Create Task and run ProvisionWorker"
    logger.debug("Creating a new VM")
    if request.method != "PUT":
        return jsonify(
            errno=2,
            message="Only PUT method is allowed"
            )
    for arg in ['name', 'package', 'hardware']:
        if arg not in request.form:
            return json.dumps(
                dict(
                    errno=1,
                    message="%s parameter was not provided" % arg))

    hardware = HardwareTemplate.query.get(request.form['hardware'])
    if not hardware:
        return jsonify(
            errno=1,
            message="HardwareTemplate %s does not exist" % (
                request.form['hardware'],))
    vm_uuid = request.form['name']
    task = Task(vm_uuid=vm_uuid)
    db.session.add(task)
    try:
        db.session.commit()
    except Exception, e:
        db.session.rollback()
        return json.dumps(
            {'errno': 1,
             'message': str(e)})
    try:
        ProvisionWorker(vm_uuid, 
                        task.ecp_uuid, 
                        hardware.ecp_uuid, 
                        request.form['package']).start()
    except Exception, e:
        return json.dumps(
            {'errno': 1,
             'message': "Could not start provision: %s" % str(e)})

    return json.dumps(
        {'errno': 0, 
         'message': "Request accepted, check transaction for status",
         'txid': task.ecp_uuid,
         'machine_id': vm_uuid})

