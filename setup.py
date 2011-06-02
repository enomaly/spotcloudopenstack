"Python Adapter for connecting OpenStack cluster with SpotCloud"

import os
from setuptools import setup, find_packages

SCRIPTS_DIR = os.path.join('src', 'spotcloudopenstack', 'bin')


CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: Apache Software License',
    'License :: OSI Approved :: MIT License',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python',
    'Topic :: Utilities',
    'Topic :: Software Development :: Libraries :: Python Modules'
]


setup(name='spotcloudopenstack',
      version='0.9',
      packages=find_packages('src'),
      package_dir = {'':'src'},
      author='DmitriKo',
      author_email='dmitrikozhevin@gmail.com',
      url="http://spotcloud.com",
      description=__doc__,
      license='Apache',
      include_package_data=True,
      classifiers=CLASSIFIERS,
      scripts = [os.path.join(SCRIPTS_DIR, 'spotcloudopenstack-init'),
                 os.path.join(SCRIPTS_DIR, 'uwsgi26')],
      install_requires=['uuid', 'boto', 'Flask-SQLAlchemy']
)
