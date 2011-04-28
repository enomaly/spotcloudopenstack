"""
Flask-SQLAlchemy Model subclusses for working with database

"""


from datetime import datetime
import uuid

from spotcloudopenstack.app import app, db
from spotcloudopenstack.novaconn import get_instance_types, get_instances_dict


class Task(db.Model):
    "Model for Tasks, mostly for provision"
    ecp_uuid = db.Column(db.String(36), primary_key=True)
    started = db.Column(db.DateTime, 
                        default=datetime.now)
    ended = db.Column(db.DateTime)
    completed = db.Column(db.Integer, default=0)# from 1 to 100
    is_error = db.Column(db.Boolean, default=False)
    vm_uuid = db.Column(db.String(36), db.ForeignKey("VM.ecp_uuid"))
    vm = db.relationship('VM')
    message = db.Column(db.Text)
    
    def __init__(self, vm_uuid):
        self.vm_uuid = vm_uuid
        self.ecp_uuid = str(uuid.uuid1())


class Package(db.Model):
    "Model from SpotCloud domain with nova_id field"
    ecp_uuid = db.Column(db.String(36), primary_key=True)
    nova_id = db.Column(db.String(80), unique=True)
    name = db.Column(db.String(80))
    storage = db.Column(db.Integer)
    os = db.Column(db.String(80))
    description = db.Column(db.Text)
    updated = db.Column(db.DateTime, 
                        default=datetime.now,
                        onupdate=datetime.now)
    state = db.Column(db.String(80))

    STATES = ('ready', 'downloading')

    def __init__(self, **kw):
        self.ecp_uuid = kw.get('ecp_uuid', str(uuid.uuid1()))
        self.os = kw.get('os', 'unknown')
        self.description = kw.get('description', '')
        self.name = kw.get('name', self.ecp_uuid)
        self.storage = kw.get('storage', 0)
        try:
            self.nova_id = kw['nova_id']
        except KeyError, e:
            raise RuntimeError(
                "%s must be provided for %s constructor" % (
                    str(e), self.__class__))
        state = kw.get('state', 'ready')
        if state not in self.STATES:
            raise RunimeError(
                "Profile state should be in %s not %s" % (
                    str(self.STATES), state))
        self.state = state

    def to_dict(self):
        "Return dict for SpotCloud API"
        return dict(
            uuid=self.ecp_uuid,
            name=self.name,
            storage=self.storage,
            os=self.os,
            description=self.description)

                   
class HardwareTemplate(db.Model):
    "Model from SpotCloud domain with nova_id field"
    ecp_uuid = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    nova_id = db.Column(db.String(80),  nullable=False)
    hypervisor_name = db.Column(db.String(12))
    cpus = db.Column(db.Integer, nullable=False)
    arch = db.Column(db.String(12))
    memory = db.Column(db.Integer, nullable=False)


    def __init__(self, **kw):
        self.ecp_uuid = kw.get('ecp_uuid', str(uuid.uuid1()))
        self.hypervisor_name = kw.get(
            'hypervisor_name', 'kvm-hvm')
        try:
            self.name = kw['name']
            self.nova_id = kw['nova_id']
            self.cpus = int(kw['cpus'])
            self.arch = kw['arch']
            self.memory = kw['memory']
        except KeyError, e:
            raise RuntimeError(
                "%s must be provided for %s constructor" % (
                    str(e), self.__class__))


    def to_dict(self):
        "Return dict for SpotCloud API"
        return dict(
            uuid=self.ecp_uuid,
            name=self.name,
            cpus=self.cpus,
            arch=self.arch,
            memory=self.memory,
            hypervisor_name=self.hypervisor_name)


    @classmethod
    def sync_with_nova(cls):
        """Delete any existed data and create 2 
        instances for each Nova's instance type 
        i386 and x86_64

        """
        cls.query.delete()
        for nova_id, memory, cpus in get_instance_types():
            for arch in ['i386', 'x86_64']:
                name = "%s.%s" % (nova_id, arch)
                obj = cls(nova_id=nova_id,
                          name=name,
                          memory=memory,
                          cpus=cpus,
                          arch=arch)
                db.session.add(obj)
                db.session.commit()


class VM(db.Model):
    ecp_uuid = db.Column(db.String(36), primary_key=True)
    nova_id = db.Column(db.String(80), unique=True)
    state = db.Column(db.String(80))
    ip_address = db.Column(db.String(80), default='127.0.0.1')
    hardware_uuid = db.Column(db.String(36), db.ForeignKey(
            'hardware_template.ecp_uuid'))
    hardware = db.relationship('HardwareTemplate')
    package_uuid = db.Column(db.String(36), db.ForeignKey(
            'package.ecp_uuid'))
    package = db.relationship('Package')
                              
    STATES = ('scheduling', 'launching', 'running')

    def __init__(self, **kw):
        self.ecp_uuid = kw.get('ecp_uuid', str(uuid.uuid1()))
        self.nova_id = kw.get('nova_id')
        state = kw.get('state', 'scheduled')
        if state not in self.STATES:
            raise RuntimeError(
                "VM state should be on from %s, got %s" % (
                    str(self.STATES), state))
        self.state = state
        if 'hardware_uuid' in kw:
            self.hardware_uuid = kw['hardware_uuid']
        else:
            if 'hardware' not in kw:
                raise RuntimeError(
                    "HardwareTemplate object or uuid should be provided")
            self.hardware_uuid = kw['hardware'].ecp_uuid
        if not 'package_uuid' in kw:
            raise RuntimeError(
                "package_uuid should be provided")
        self.package_uuid = kw['package_uuid']
    
    def to_dict(self):
        "Return dict representation for SpotCloud API"
        return dict(
            uuid=self.ecp_uuid,
            name=self.ecp_uuid,
            state=self.state,
            nova_id=self.nova_id,
            ip_address=self.ip_address)

            
    @classmethod
    def sync_with_nova(cls):
        "Sync VM states from Nova with db"
        nova_instances = get_instances_dict()
        for vm in cls.query.all():
            if vm.nova_id not in nova_instances:
                db.session.delete(vm)
                db.session.commit()
                continue
            nova_instance = nova_instances[vm.nova_id]
            updated = False
            if vm.ip_address != nova_instance.dns_name:
                vm.ip_address = nova_instance.dns_name
                updated = True
            if vm.state != nova_instance.state:
                vm.state = nova_instance.state
                updated = True
            if updated:
                db.session.add(vm)
                db.session.commit()


def init_db(uri=None):
    """
    Drop then create all tables,
    fill them with initial data

    """
    if uri:
        app.config['SQLALCHEMY_DATABASE_URI'] = uri
    
    db.drop_all()
    db.create_all()
    HardwareTemplate.sync_with_nova()    

    

