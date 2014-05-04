#!/usr/bin/env python
# file added by mbs, 2014-05-04

from setuptools import setup
import os
from setuptools import setup, find_packages
 
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
 
print 'os: %s' % os.environ.get('OPENSHIFT_REPO_DIR', PROJECT_ROOT)

setup(
    name='bioco-wip',
    version='0.00001',
    description='OpenShift App',
    author='Your Name',
    author_email='example@example.com',
    url='http://www.python.org/sigs/distutils-sig/',
    #install_requires=['Django==1.6'],
    install_requires=open('%s/requirements.txt' % os.environ.get('OPENSHIFT_REPO_DIR', PROJECT_ROOT)).readlines()
)
