#!/usr/bin/env python

# Make Debian package for ddr-local
#
# $ cd ddr-local
# $ python debian/package.py

import os
import re
import subprocess
import sys

def subcall(cmd):
    print(cmd)
    status = subprocess.check_call(cmd, shell=True, executable='/bin/bash')
    print(status)
    if status:
        system.exit(1)

PROJ_NAME='ddr-local'
APP_NAME='ddrlocal'
ARCHITECTURE='i386'
print('PROJ_NAME: {}'.format(PROJ_NAME))
print('APP_NAME: {}'.format(APP_NAME))
print('ARCHITECTURE: {}'.format(ARCHITECTURE))

# extract the first (most recent) date from changelog
# assumes you're running from outside the debian/ dir.
VERSION = None
changelog_path = 'debian/changelog'
if not os.path.exists(changelog_path):
    print("No changelog file")
    sys.exit(1)
with open(changelog_path,'r') as cl:
    changelog = cl.readlines()
versions = []
for line in changelog:
    match = re.search('(\d+.\d\d\d\d\d\d\d\d)', line)
    if match:
        versions.append(match.group(0))
if not versions:
    print("Couldn't get a version from changelog")
    sys.exit(1)
VERSION = versions[0]
print('VERSION: {}'.format(VERSION))

VENV="env/ddr-local"
DESTDIR="/tmp"
PKGINSTALLDIR="/opt"
print('VENV: {}'.format(VENV))
print('DESTDIR: {}'.format(DESTDIR))
print('PKGINSTALLDIR: {}'.format(PKGINSTALLDIR))

# use pip2pi to cache pypi downloads
#PIPCACHE="http://127.0.0.1/pypackages/simple/"
PIPCACHE=""

SRCDIR=os.getcwd()
PKG='{}-{}'.format(PROJ_NAME, VERSION)
DEB='{}_{}'.format(PROJ_NAME, VERSION)
PKGDIR="{}/{}".format(DESTDIR, PKG)
PIPLOG="{}/{}-pip.log".format(DESTDIR, PKG)
DEBFINAL="{}/{}_{}.deb".format(DESTDIR, DEB, ARCHITECTURE)
VENVDIR="{}/{}".format(PKGDIR,VENV)
SHBANGDIR="{}/{}/bin/".format(PKGDIR, VENV)
FINALVENVDIR="/opt/virtualenvs/{}".format(PROJ_NAME)
print('SRCDIR: {}'.format(SRCDIR))
print('PKG: {}'.format(PKG))
print('DEB: {}'.format(DEB))
print('PKGDIR: {}'.format(PKGDIR))
print('PIPLOG: {}'.format(PIPLOG))
print('DEBFINAL: {}'.format(DEBFINAL))
print('VENVDIR: {}'.format(VENVDIR))
print('SHBANGDIR: {}'.format(SHBANGDIR))
print("FINALVENVDIR: {}".format(FINALVENVDIR))

# use s=...=...= instead of s/.../.../ so don't have to escape slashes in paths
#SEDCMD="s=#!${PKGDIR}/${APP_NAME}/${VENV}/bin/python=#!${PKGINSTALLDIR}/${APP_NAME}/${VENV}/bin/python="
SEDCMD="s={}/{}={}=".format(PKGDIR, VENV, FINALVENVDIR)
print("SEDCMD: {}".format(SEDCMD))

# make sure we have Debian package tools
if '/usr/bin/debuild' not in subprocess.check_output('whereis debuild', shell=True):
    print("Install Debian packaging tools:")
    print("    apt-get install build-essential debhelper cdbs dh-make diffutils patch gnupg fakeroot lintian devscripts pbuilder dpatch dput quilt")
    sys.exit(1)

# make sure we have pg_config (dependency for psycopg2)
if '/usr/bin/pg_config' not in subprocess.check_output('whereis pg_config', shell=True):
    print("Install psycopg2 dependency:")
    print("    apt-get install libpq-dev python-dev")
    sys.exit(1)

#if [ `basename "$PWD"` != $PROJ_NAME ]; then
#  echo "ERROR: Script must be run from the ${PROJ_NAME} project root directory."
#    sys.exit(1)
#fi

# rm old builds
if os.path.exists(PKGDIR):
    print("Removing old tmp packages: {}".format(PKGDIR))
    subcall('rm -Rf {}'.format(PKGDIR))

# copy code to build location
print("Copying {} to {}".format(SRCDIR, PKGDIR))
subcall('cp -R {} {}'.format(SRCDIR,PKGDIR))

# Build a complete and self-contained virtualenv in the *package* destination dir.
# NOTE: virtualenv is not inside the project dir.
print("Building virtualenv: {}".format(VENVDIR))
os.chdir(PKGDIR)
subcall('virtualenv --no-site-packages --python=python2.7 {}'.format(VENVDIR))
SOURCE = 'source {}/{}/bin/activate'.format(PKGDIR,VENV)
subcall(SOURCE)
if PIPCACHE:
    print("Using pipcache: {}".format(PIPCACHE))
    subcall('{} && pip install -vv --index-url={} -r {}/{}/requirements/production.txt --log {}'.format(SOURCE, PIPCACHE, PKGDIR, APP_NAME, PIPLOG))
else:
    print("No pipcache")
    subcall('{} && pip install -vv -r {}/{}/requirements/production.txt --log {}'.format(SOURCE, PKGDIR, APP_NAME, PIPLOG))

# Adjust all the files in the virtualenv's bin/ dir to point to the
# final virtualenv location rather than the temporary location inside
# the build directory.
print("Fixing shbang paths in {}".format(SHBANGDIR))
os.chdir(PKGDIR)
subcall('find {} -type f | xargs -n1 -i sed -i {} {{}}'.format(SHBANGDIR, SEDCMD))

# build it
print("Building package")
os.chdir(PKGDIR)
subcall('debuild -rfakeroot -us -uc ')

# go back to orig directory
os.chdir(SRCDIR)
print("Finished package: {}".format(DEBFINAL))
sys.exit(0)
