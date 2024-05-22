# INSTALL

For more complete instructions, see the "Admins/Workstations" section
in `ddr-manual <https://github.com/denshoproject/ddr-manual/>`_.

The `ddr-local` install and update scripts below have been tested on
Debian 11 running as a VM in VirtualBox.


## Three Ways To Install

There are three ways to install `ddr-local`:

- package file (.deb)
- package repository (apt-get)
- manual (git clone)


### Package File Install (.deb)

If you have a `ddrlocal-BRANCH_VERSION_ARCH.deb` file you can install
using the `gdebi` command.  The `virtualenv` is installed ready to go
and Debian packaged dependencies (Nginx, Redis, etc) are automatically
installed as required.
``` bash
sudo apt-get install gdebi
sudo gdebi ddrlocal-BRANCH_VERSION_ARCH.deb
```

The result is the same as a manual install but is faster since you
don't have to build the virtualenv and lets you completely remove the
install if you so choose.

You are not done when the install completes!  See the Post-Install
section below for instructions on configuration.

NOTE: you will **not** receive automatic updates from the repository!

**Uninstalling**

See the "Uninstalling" heading under the next section.


### Package Repository Install (apt-get)

It is recommended to install `ddr-local` from a package repository
so that your install will receive upgrades automatically along with
other packages.

**Adding the Repository**

To use our repository you must first add the packaging signing key
using the `apt-key` tool and then add the repository itself to your
list of APT sources. Commands for accomplishing this are listed below
(for completeness we include commands to install curl and the apt
tools - you may already have these installed).
``` bash
sudo apt-get update && sudo apt-get install curl apt-transport-https gnupg
sudo curl -s http://packages.densho.org/debian/keys/archive.asc | sudo apt-key add -
echo "deb http://packages.densho.org/debian/ jessie main" | sudo tee /etc/apt/sources.list.d/packages_densho_org_debian.list
```

**Installing the Package**

You can now install the DDR Editor with a single command:
``` bash
sudo apt-get update && sudo apt-get install ddrlocal-master
```

Switching Git branches in a package install is not recommended, as updates will
likely damage your install.  If you want to switch branches you should consider
a source install.

You are not done when the install completes!  See the Post-Install
section below for instructions on configuration.

**Uninstalling**

A normal `apt-get remove` uninstalls the software from your system,
leaving config and data files in place.
``` bash
sudo apt-get remove ddrlocal-master
```

To completely remove all files installed as part of `ddr-local`
(e.g. configs, static, and media files), use `apt-get purge`.
IMPORTANT: this removes the `/media/` directory which contains your
data!
``` bash
sudo apt-get purge ddrlocal-master
sudo rm /etc/apt/sources.list.d/packages_densho_org_debian.list && apt-get update
```


## Manual Install (git clone)

You can also install manually by cloning the `ddr-local` Git repository.
This method requires you to build the `virtualenv` and install prerequisites
but is the best method if you are going to work on the `ddr-local` project.

Technically you can clone `ddr-local` anywhere you want but `make install` will
attempt to install the app in `/opt/ddr-local` so you might as well just clone
it to that location.
``` bash
sudo apt-get update && sudo apt-get upgrade
sudo apt-get install git make
sudo git clone https://github.com/denshoproject/ddr-local.git /opt/ddr-local
cd /opt/ddr-local/
```

Git-cloning and downloading static files are a separate step from the
actual installation.  GitHub may ask you for passwords.
``` bash
cd /opt/ddr-local/
sudo make get
```

If you want to work on this application or if you just want to try the
latest in-development code, switch to the `develop` branch of each
repository. Do this before running `make install`.
``` bash
cd /opt/ddr-local/ddr-cmdln; git checkout develop
cd /opt/ddr-local/ddr-defs; git checkout develop
cd /opt/ddr-local/densho-vocab; git checkout develop
cd /opt/ddr-local; git checkout develop
```

This step installs dependencies from Debian packages, installs Python
dependencies in a virtualenv, and places static assets and config
files in their places.
``` bash
cd /opt/ddr-local/
sudo make install
```

Problems installing `lxml` may be due to memory constraints,
especially if Elasticsearch is running, which it will be if you've
done `make enable-bkgnd`.

Install config files.
``` bash
cd /opt/ddr-local/
sudo make install-configs
```

If you want to modify any of the files you must give yourself permissions.
``` bash
sudo chown -R USER.USER /opt/ddr-local
```


## POST-INSTALL


### The DDR user

IMPORTANT: The editor must run as the `ddr` user, which is installed
as part of the package install.  The `ddr` user should be installed
automatically.  In the Densho HQ environment, it is *critical* that
the `ddr` user has the uid and gid set to `1001`.
``` bash
cd /opt/ddr-local/
sudo make ddr-user
```


### Usage

In order to use `ddr-local` you must activate its `virtualenv` which
is located in `/opt/ddr-local/venv/ddrcmdln`.
``` bash
USER@HOST:~$ su ddr
ddr@HOST:~$ source /opt/ddr-cmdln/venv/ddrcmdln/bin/activate
(ddrcmdln)ddr@HOST:~$
```


### Gitolite keys

The `ddr` user requires SSL keys in order to synchronize local
collection repositories with those on the main Gitolite server.  Setup
is beyond this INSTALL so please see `ddr-manual`.


### Repository Directory

Once your `ddr` user has its gitolite keys (see "Gitolite keys" step)
you can create a directory for collections.  If your install does not
use `/var/www/media/ddr` please update the following values in
`/etc/ddr/ddrlocal-local.cfg`.
``` bash
[local] base_path
[local] media_root
[cmdln] media_base
```

Create the repository directory.
``` bash
sudo mkdir -p /var/www/media/ddr
sudo chown -R ddr.ddr /var/www/media/ddr
```

Clone the `ddr` repository repo, the `ddr-testing` and `ddr-densho`
organization repos, and the `ddr-densho-10` collection repo which
is used for running unit tests.
``` bash
sudo -u ddr git clone git@mits.densho.org:ddr.git           /var/www/media/ddr/ddr
sudo -u ddr git clone git@mits.densho.org:ddr-testing.git   /var/www/media/ddr/ddr-testing
sudo -u ddr git clone git@mits.densho.org:ddr-densho.git    /var/www/media/ddr/ddr-densho
sudo -u ddr git clone git@mits.densho.org:ddr-densho-10.git /var/www/media/ddr/ddr-densho-10
```


### Unit Tests

In order for unit tests to work, you must have 1) installed `ddr-local` using
one of the above methods, 2) created a `ddr` user, 3) installed Gitolite keys,
and 4) created the repository directory and test repos.
``` bash
cd /opt/ddr-local/
sudo su ddr
source /opt/ddr-local/venv/ddrlocal/bin/activate
make test
```


### Makefile

The `ddr-local` makefile has a number of useful options for
installing, removing, stopping, restarting, and otherwise interacting
with parts of the editor.  Run `make` with no arguments for a list or
(better) look through the Makefile itself.
``` bash
cd /opt/ddr-local/
make
```


### Settings Files

Default settings are in `/etc/ddr/ddrlocal.cfg`.  Please do not edit
this file.  Settings in `/etc/ddr/ddrlocal-local.cfg` will override
the defaults.

Rather than listing settings files here, examine the `deb` task in
`Makefile`, as all the config files are listed there.


### Models Definitions

If you installed from a package the latest model definitions should be
installed in the `ddr-local` directory.  If you installed from source
the definitions should have been downloaded as part of `make get`.  If
for some reason they are absent you can clone a copy thusly:
``` bash
cd /opt/ddr-local/
sudo make get-ddr-defs
```

If you want to install the model definitions in some non-standard
location, you can clone them:
``` bash
sudo git clone https://github.com/denshoproject/ddr-defs.git /PATH/TO/ddr-defs/
```


### Network Config

The Makefile can install a networking config file which sets the VM
to use a standard IP address (192.168.56.101).
``` bash
cd /opt/ddr-local/
sudo make network-config
sudo reboot
```

Network config will take effect after the next reboot.


### Firewall Rules

If you want to access Supervisor or Elasticsearch via a web browser,
open ports in the firewall.
``` bash
sudo ufw allow 9001/tcp  # supervisor
sudo ufw allow 9200/tcp  # elasticsearch
```


### VirtualBox Guest Additions

The Makefile can install VirtualBox Guest Additions, which is required
for accessing shared directories on the host system.
``` bash
cd /opt/ddr-local/
sudo make vbox-guest
```

This step requires you to click "Devices > Insert Guest Additions CD
Image" in the device window.


### Switching Branches

*Package Install*

The DDR editor is available in two branches: master and develop.
The master branch is more stable and is intended for production use.
The develop branch is for more cutting edge features that may not be quite ready for the master branch.

It is not recommended that you switch branches manually, as updates will probably damage your install.
If you wish to use the develop branch instead of the master branch, remove `ddrlocal-master` and install `ddrlocal-develop`.
``` bash
sudo apt-get remove ddrlocal-master
sudo apt-get install ddrlocal-develop
```

*Source Install*

Once you have everything installed, if you need to work on a different branch of the code you may need to make sure that the entire codebase (`ddr-local`, `ddr-cmdln`, and `ddr-defs`) is on the same branch.

These lines check out the specified branch, download and install Python dependencies for each project, and compile/install `ddr-cmdln`.  These steps are all necessary, or new code may not have the proper dependencies.
``` bash
# cd /opt/ddr-local
# git checkout -b $BRANCH origin/$BRANCH # <<< If branch does not yet exist.
# git checkout $BRANCH                   # <<< If updating existing branch.
# pip install -U -r requirements/production.txt
# python setup.py install
# cd /usr/local/src/ddr-local/ddrlocal
# git checkout -b $BRANCH origin/$BRANCH # <<< If branch does not yet exist.
# git checkout $BRANCH                   # <<< If updating existing branch.
# pip install -U -r requirements/production.txt
```

Newer branches have a `make branch` task designed to automate as much of this as possible.  For example, switching to the `batch-edit` branch:
``` bash
make branch BRANCH=batch-edit
```

Some branches may use a branch of the 'ddr' repo.  If so then you must switch branches on the 'ddr' repo and restart.
``` bash
# cd /var/www/media/base/ddr/
# git checkout -b $BRANCH origin/$BRANCH # <<< If branch does not yet exist.
# git checkout $BRANCH                   # <<< If updating existing branch.
# cd /usr/local/src/ddr-local/ddrlocal
```

After switching branches, you must copy new versions of the config files and restart before changes will take effect.
``` bash
# make reload
# make restart
```
