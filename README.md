### SpotCould OpenStack Adapter
This soft converts your dull Ubuntu boxes to the shiny cash machine ;)

#### Overview
##### The easiest part
This is Python WSGI application that translates SpotCloud HTTP calls  
to EC2 API that exposed by your OpenStack installation.	  

It uses SQLAlchemy for the persistence service and you could find the  
code very straightforward. 

##### The tricky part
SpotCloud used .xvm2 files to provide VirtualMachine (VM).  
This file is just a tar archive with gziped RAW disk image and some metadata.  
But OpenStacks need a compatible kernel/ramdisk pair and  
VM image in different format

So SpotCloudOpenStack download .xvm2, untrar and unzip,  
extract kernel/ramdisk, convert partition with VM  to QCOW2 format,  
make tar.gz and publish it with  uec-publish-tarball command. Phew!  

 
#### To be done.
There is a plan to make deb package and init scripts.  
Utilization method not implemented yet too.

#### Install
It assumes you have an admin user and a project created.    

See http://wiki.openstack.org/RunningNova  

`$ sudo python setup.py install`  

Now you have sptocloudopenstack-init in /usr/bin.  

`$ sudo spotcloudopenstack-init USER_NAME PROJECT_NAME`  

USER_NAME and PROJECT_NAME are created by nova-manage  

Please, note, it will ask you for user name and password that you are   
going to use for SpotCloud

#### Run
Since this is good old WSGI application, there is a lot of ways to run it.  

Installer put uwsgi26 binary in your /usr/bin and   
wsgi.py to /var/lib/spotcloudopenstack  

You could run it behind the proxy with something like this:  

` $ uwsgi --http 127.0.0.1:8080  --file /var/lib/spotcloudopenstack/wsgi.py  --socket /tmp/uwsgi.socket --processes=4`

Or run it by Nginx with uwsgi hander. See http://projects.unbit.it/uwsgi/wiki/RunOnNginx  

You could find plenty other ways - see http://projects.unbit.it/uwsgi/  

#### Thanks
Thank you guys, for all your questions and suggestions sent directly to  dmitrikozhevin@gmail.com.  
Thanks Reuven Cohen for the brilliant ideas and Enomaly for the sponsorship.  


