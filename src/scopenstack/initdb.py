"""
Drop and create all needed tables in the Database.
Run it from account with ability to run nova-manager.
Usually that means run 
$ . novarc 
incide your home folder

"""

from scopenstack.models import init_db

if __name__ == '__main__':
    init_db()
