"""
Create a VM.
If needed download a .XVM2 and convet it in Nova Image

"""

from threading import Thread
import time
import os
import urllib
from subprocess import call, Popen, PIPE
import tarfile
import shutil
import re
from glob import glob

from spotcloudopenstack.models import Package, HardwareTemplate, Task, VM
from spotcloudopenstack.novaconn import get_nova_connection, get_instance_id
from spotcloudopenstack.app import app, db

import logging
logger = logging.getLogger('spotcloudopenstack')


DOWNLOAD_LIMIT = 30*60 #sec


class ProvisionWorker(Thread):
    """If needed Download XVM2 file
    convert it to OpenStack image and publish it.
    Create a VM
    """
    def __init__(self, vm_uuid, task_uuid, hardware_uuid, package_uuid):
        Thread.__init__(self)
        self.vm_uuid = vm_uuid
        self.task_uuid = task_uuid
        self.hardware_uuid = hardware_uuid
        self.package_uuid = package_uuid
        self.nova_connection = get_nova_connection()

    def run(self):
        try:
            self._run()
        except Exception, e:
            logger.error(str(e))
            task = Task.query.get(self.task_uuid)
            vm = VM.query.get(self.vm_uuid)
            task.message = str(e)
            task.is_error = True
            task.completed = 100 
            db.session.add(task)       
            if vm:
                db.session.delete(vm)
            db.session.commit()

    def _run(self):
        logger.debug('going to create vm %s', self.vm_uuid)
        hardware = HardwareTemplate.query.get(
            self.hardware_uuid)
        if not hardware:
            raise RuntimeError(
                "Could not get hardware %s" % self.vm.hardware_uuid)

        package = self.get_or_download_pkg(
            self.package_uuid, hardware.arch)

        logger.debug('Creating Instance from %s',  package.nova_id)
        reservation = self.nova_connection.run_instances(
            package.nova_id,
            instance_type=hardware.nova_id,
            addressing_type='private',
            min_count=1,
            max_count=1)
        self.instance_created(get_instance_id(reservation.id))


    def instance_created(self, nova_id):
        "Update database with newly created nova instance id"
        logger.debug('Nova instance created')
        vm = VM(
            ecp_uuid=self.vm_uuid,
            state='scheduling', 
            hardware_uuid=self.hardware_uuid,
            package_uuid=self.package_uuid,
            nova_id=nova_id)
        task = Task.query.get(self.task_uuid)
        task.completed = 100
        task.message = 'Provision %s OK' % self.vm_uuid
        db.session.add(vm)
        db.session.add(task)
        db.session.commit()
        logger.debug('Provision OK')


    def _download_pkg(self, pkg_uuid):
        "Download package inside repo dir"
        target_dir = os.path.join(
            app.config['REPO_DIR'], pkg_uuid)
        if not os.path.exists(target_dir):
            os.mkdir(target_dir)
        os.chdir(target_dir)
        url = app.config['PACKAGE_DOWNLOAD_URL_TMPL'] % pkg_uuid
        logger.debug('going to download %s', url)
        file_, headers = urllib.urlretrieve(
            url, 'package.xvm2')
        logger.debug('download completed')
        return target_dir, file_
    

    def _extract_disk(self, working_dir, file_name):
        "Extract disk image, unzip it, return its name"
        def get_disk_name(pkg_file):
            "find and return disk file tar memeber"
            for member in pkg_file.getmembers():
                if member.name.endswith('.gz'):
                    return member
            raise RuntimeError(
                "Could not find disk file in %s" % pkg_file.name)
        pkg_file = tarfile.open(
            os.path.join(working_dir, file_name))
        disk_file = get_disk_name(pkg_file)
        os.chdir(working_dir)
        pkg_file.extract(disk_file)
        logger.debug('unzipping disk')
        if call(['gunzip', '-f', disk_file.name]):
            raise RuntimeError(
                "Could not gunzip %s" % disk_file.name)
        logger.debug('done')
        return disk_file.name[:-3]


    def _get_offset(self, file_path):
        "Calculate offset for mounting"
        proc = Popen(['file', file_path], stdout=PIPE, stdin=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode:
            raise RuntimeError(
                "Could not get info about %s, got: %s" % (
                    file_path, stderr))
        match = re.search('startsector\W(\d+)', stdout)
        if match is None:
            raise RuntimeError(
                "Could not parse file info %s" % (
                    stdout))
        return int(match.group(1)) * 512

        
    def _mount_disk(self, working_dir, file_name):
        "Mount first partition from disk file"
        file_path = os.path.join(working_dir, file_name)
        offset = self._get_offset(file_path)
        mount_dir = os.path.join(working_dir, 'mnt')
        if not os.path.exists(mount_dir):
            os.mkdir(mount_dir)
        if call(['sudo',
                 'mount', 
                 '-o', 
                 'loop,offset=%s' % offset, 
                 file_path,
                 mount_dir]):
            raise RuntimeError(
                "Could not mount %s to %s with offset %s" % (
                    file_path, mount_dir, offset))
        return mount_dir


    def _copy_initrd(self, working_dir, mount_dir, pkg_uuid):
        "Copy initrd from mounted vm disk"
        boot_dir = os.path.join(mount_dir, 'boot')
        files = glob(os.path.join(boot_dir, 'initrd.*'))
        if not files:
            raise RuntimeError(
                "Could not find initrd image in vm disk boot dir")
        target_file_path = os.path.join(
            working_dir,
            "%s-initrd" % pkg_uuid)
        shutil.copy(files[0], target_file_path)
        return target_file_path


    def _copy_vmlinuz(self, working_dir, mount_dir, pkg_uuid):
        "Copy vmlinuz from mounted vm disk"
        boot_dir = os.path.join(mount_dir, 'boot')
        files = glob(os.path.join(boot_dir, 'vmlinuz*'))
        if not files:
            raise RuntimeError(
                "Could not find vmlinuz image in vm disk boot dir")
        target_file_path = os.path.join(
            working_dir,
            "%s-vmlinuz" % pkg_uuid)
        shutil.copy(files[0], target_file_path)
        return target_file_path


    def _get_loop_dev(self, working_dir):
        "Return loop device name used for mount"
        proc = Popen(['sudo', 'losetup', '-a'],
                     stdout=PIPE,
                     stderr=PIPE)
        stdout, stderr = proc.communicate()
        if stderr:
            raise RuntimeError(
                "Could not get list of loop devices %s" % (
                    stderr, ))
        for line in stdout.split('\n'):
            match = re.search('^/dev/loop(\d+):[^\(]+\(([^\)]+)\)', line)
            if match:
                loop_dev = "/dev/loop%s" % match.group(1)
                dir_name = os.path.dirname(match.group(2))
                if dir_name == working_dir:
                    return loop_dev
        raise RuntimeError(
            "Could not find loop device for %s" % working_dir)
        

    def _copy_root_fs(self, working_dir, mount_dir):
        "Put content of directory to raw img"
        loop_dev = self._get_loop_dev(working_dir)
        target_file_path = os.path.join(working_dir, 
                                        'temp.img')
        if call(['dd', 'if=%s' % loop_dev,
                 'of=%s' % target_file_path,
                 'bs=1024']):
            raise RuntimeError(
                "Could not copy from %s to %s" % (
                    loop_dev, target_file_path))
        return target_file_path


    def _convert_raw2qcow(self, working_dir, src_file_path, pkg_uuid):
        "Convert raw image to qcow2"
        target_file_path = os.path.join(working_dir, 
                                        "%s.img" % pkg_uuid)
        if call(
            ['qemu-img',
             'convert',
             '-f', 'raw',
             src_file_path,
             '-O', 'qcow2',
             target_file_path]):
            raise RuntimeError(
                "Could not convert %s to qcow2" % (
                    src_file_path,))
        os.unlink(src_file_path)
        return target_file_path
    

    def _download_and_convert_pkg(self, pkg_uuid, arch):
        """Download .xvm2,
        extract disk file from it,
        from this file extract vmlinuz and initrd and root file system,
        convert root file system to qcow2 image,
        create .tar.gz and publish it with uec tools

        """
        working_dir, file_name = self._download_pkg(pkg_uuid)
        disk_file_name = self._extract_disk(working_dir, file_name)
        mount_dir = self._mount_disk(working_dir, disk_file_name)
        initrd = self._copy_initrd(working_dir, mount_dir, pkg_uuid)
        vmlinuz = self._copy_vmlinuz(working_dir, mount_dir, pkg_uuid)
        root_fs = self._copy_root_fs(working_dir, mount_dir)
        qcow_img = self._convert_raw2qcow(working_dir, root_fs, pkg_uuid)
        if call(['sudo', 'umount', mount_dir]):
            logger.warning("Could not umount %s" % mount_dir)
        os.unlink(os.path.join(working_dir, disk_file_name))
        image_nova_id = self._publish_image(
            initrd, vmlinuz, qcow_img, pkg_uuid, arch)
        
        package = Package(ecp_uuid=pkg_uuid,
                          nova_id=image_nova_id)
        db.session.add(package)
        db.session.commit()
        return package


    def _publish_image(self, initrd, vmlinuz, img, pkg_uuid, arch):
        "Publish image with uec tool"
        tar_name = "%s.tar.gz" % pkg_uuid
        logging.debug("making %s", tar_name)
        if call(
            ['tar', 'czvf',
             tar_name,
             os.path.basename(initrd), 
             os.path.basename(vmlinuz), 
             os.path.basename(img)]):
            raise RuntimeError(
                "could not make %s" % tar_name)
        logger.debug('made %s', tar_name)
        proc = Popen(
            [app.config['PUBLISH_SCRIPT'],
             tar_name,
             pkg_uuid[:7],
             arch], 
            stdout=PIPE,
            stderr=PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode:
            raise RuntimeError(
                "Could not publish image, %s" % (
                    stderr,))
        emi = stdout.strip().split('\n')[-1].split()[0]
        match = re.search('emi=\W([^\"]+)', emi)
        if match:
            # TODO remove files that already in tar.gz
            return match.group(1)
        else:
            raise RuntimeError(
                "Could not get image id from %s" % emi)


    def get_or_download_pkg(self, pkg_uuid, arch):
        """"Return package object if it is in database,
        run _download_and_convert other way

        """
        package = Package.query.get(pkg_uuid)
        if package is None:
            return self._download_and_convert_pkg(pkg_uuid, arch)
        started = time.time()
        while package.state == 'downloading': # in another thread
            if (time.time() - started) > DOWNLOAD_LIMIT:
                raise RuntimeError(
                    "Time limit for package download is reached.")
            time.sleep(5)
            db.session.refresh(package)
        return package
