"Python Adapter for connecting OpenStack cluster with SpotCloud"

from setuptools import setup, find_packages

CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: Apache Software License',
    'License :: OSI Approved :: MIT License',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python',
    'Topic :: Utilities',
    'Topic :: Software Development :: Libraries :: Python Modules'
]

setup(name='scopenstack',
      version='0.3',
      packages=find_packages('src'),
      package_dir = {'':'src'},
      author='DmitriKo',
      author_email='dmitrikozhevin@gmail.com',
      url="http://spotcloud.com",
      license='Apache',
      include_package_data=True,
      classifiers=CLASSIFIERS,
      install_requires=['uuid', 'boto', 'Flask-SQLAlchemy']
)
