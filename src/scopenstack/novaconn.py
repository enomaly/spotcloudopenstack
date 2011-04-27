"""
Interact with Nova system
via EC2 API and command line tools

"""

from subprocess import Popen, PIPE

from scopenstack.client import NovaAdminClient
from scopenstack.app import app

def get_nova_connection():
    """Return Admin Client connection to communicate with
    Nova via HTTP API

    """
    nova = NovaAdminClient(
        clc_url = app.config['NOVA_ENDPOINT'],
        region = app.config['NOVA_REGION'],
        access_key = app.config['NOVA_ACCESS_KEY'],
        secret_key = app.config['NOVA_SECRET_KEY'])

    return nova.connection_for(app.config['USERNAME'], 
                               app.config['PROJECT_NAME'])

    
def nova_manage(*args):
    "Run nova-manage command and return output"
    cmd = list(args)
    cmd.insert(0, app.config['NOVA_MANAGE'])
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr =  proc.communicate()
    if stderr:
        raise RuntimeError(
            "Could not run nova manage with %s" % str(args))
    return stdout


def get_instances_dict():
    """Return dict of running instances from Nova.
    key is nova_id, value is an instance
    """
    result = {}
    conn = get_nova_connection()
    for reservation in conn.get_all_instances():
        for instance in reservation.instances:
            result[instance.id] = instance
    return result


def get_instance_id(reservation_id):
    "Return instance id for first instance from reservation"
    conn = get_nova_connection()
    for reservation in conn.get_all_instances():
        if reservation.id == reservation_id:
            for instance in reservation.instances:
                return instance.id
    return None


def get_instance_types():
    """Return a list of available intance types.
    Each insance type is a tuple (name, memory, vcpu)

    """
    import re
    result = []
    output = nova_manage('instance_type', 'list')
    lines = [x.strip() for x in output.split('\n') if x.strip()]
    for line in lines:
        try:
            nova_name = re.search('^([^\:]+)', line).group(1)
            memory = re.search('Memory:\s+(\d+)', line).group(1)
            cpus = re.search('VCPUS:\s+(\d+)', line).group(1)
        except (AttributeError, IndexError):
            raise RuntimeError(
                "Could not parse nova-manage output %s" % line)
        result.append((nova_name, memory, cpus))
    return result
