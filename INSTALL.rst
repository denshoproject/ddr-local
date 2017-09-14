INSTALL
=======

For more complete instructions, see the "Admins/Workstations" section
in `ddr-manual <https://github.com/densho/ddr-manual/>`_.

The `ddr-local` install and update scripts below have been tested on
Debian 8.0 running as a VM in VirtualBox.


Three Ways To Install
---------------------

There are three ways to install `ddr-local`:

- package file (.deb)
- package repository (apt-get)
- manual (git clone)


Package File Install (.deb)
---------------------------

If you have a `ddrlocal-BRANCH_VERSION_ARCH.deb` file you can install
using the `gdebi` command.  The `virtualenv` is installed ready to go
and Debian packaged dependencies (Nginx, Redis, etc) are automatically
installed as required.
::
    $ sudo apt-get install gdebi
    $ sudo gdebi ddrlocal-BRANCH_VERSION_ARCH.deb
    ...

The result is the same as a manual install but is faster since you
don't have to build the virtualenv and lets you completely remove the
install if you so choose.

After the install completes you can use `make` commands to manage the
installation.

NOTE: you will **not** receive automatic updates from the repository!

**Uninstalling**

See the "Uninstalling" heading under the next section.


Package Repository Install (apt-get)
------------------------------------

It is recommended to install `ddr-local` from a package repository,
since your install will receive upgrades automatically along with
other packages.

**Adding the Repository**

To use our repository you must first add the packaging signing key
using the `apt-key` tool and then add the repository itself to your
list of APT sources. Commands for accomplishing this are listed below
(for completeness we include commands to install curl and the apt
tools - you may already have these installed).
::
    $ sudo apt-get update && sudo apt-get install curl apt-transport-https gnupg
    ...
    $ sudo curl -s http://packages.densho.org/debian/keys/archive.asc | sudo apt-key add -
    ...
    $ echo "deb http://packages.densho.org/debian/ jessie main" | sudo tee /etc/apt/sources.list.d/packages_densho_org_debian.list
    ...

**Installing the Package**

You can now install the DDR Editor with a single command:
::
    $ sudo apt-get update && sudo apt-get install ddrlocal-master
    ...

If you wish to use the develop branch instead of the master branch,
remove `ddrlocal-master` and install `ddrlocal-develop`.  Switching
branches in a package install is not recommended, as updates will
probably damage your install.  If you want to switch branches you
should consider a source install.

Now you should be able to run mailpile on the command line and join
the fun! If you have installed the Apache integration, you can access
https://your.example.com/mailpile/ and log on that way.

**Uninstalling**

A normal `apt-get remove` uninstalls the software from your system,
leaving config and data files in place.
::
    $ sudo apt-get remove ddrlocal-master
    ...

To completely remove all files installed as part of `ddr-local`
(e.g. configs, static, and media files), use `apt-get purge`.
IMPORTANT: this removes the `/media/` directory which contains your
data!
::
    $ sudo apt-get purge ddrlocal-master
    ...
    $ sudo rm /etc/apt/sources.list.d/packages_densho_org_debian.list && apt-get update
    ...


Manual Install (git clone)
--------------------------

You can also install manually by cloning the `ddr-local` Git
repository.  This method requires you to build the `virtualenv` and
install prerequisites but is the best method if you are going to work
on the `ddr-local` project.

Technically you can clone `ddr-local` anywhere you want but `make
install` will attempt to install the app in `/opt/ddr-local` so you
might as well just clone it to that location.
::
    $ sudo apt-get update && apt-get upgrade
    $ sudo apt-get install git make
    $ sudo git clone https://github.com/densho/ddr-local.git /opt/ddr-local
    $ cd /opt/ddr-local/

Git-cloning and downloading static files are a separate step from the
actual installation.  GitHub may ask you for passwords.
::
    $ cd /opt/ddr-local/
    $ sudo make get

This step installs dependencies from Debian packages, installs Python
dependencies in a virtualenv, and places static assets and config
files in their places.
::
    $ cd /opt/ddr-local/
    $ sudo make install

Problems installing `lxml` may be due to memory constraints,
especially if Elasticsearch is running, which it will be if you've
done `make enable-bkgnd`.


POST-INSTALL
============


Makefile
--------

The `ddr-local` makefile has a number of useful options for
installing, removing, stopping, restarting, and otherwise interacting
with parts of the editor.  Run `make` with no arguments for a list or
(better) look through the Makefile itself.
::
    $ make


Settings Files
--------------

Default settings are in `/etc/ddr/ddrlocal.cfg`.  Please do not edit
this file.  Settings in `/etc/ddr/ddrlocal-local.cfg` will override
the defaults.

Rather than listing settings files here, examine the `deb` task in
`Makefile`, as all the config files are listed there.


Models Definitions
------------------

If you installed from a package the latest model definitions should be
installed in the `ddr-local` directory.  If you installed from source
the definitions should have been downloaded as part of `make get`.  If
for some reason they are absent you can clone a copy thusly:
::
    $ sudo make get-ddr-defs

If you want to install the model definitions in some non-standard
location, you can clone them:
::
    $ sudo git clone https://github.com/densho/ddr-defs.git /PATH/TO/ddr-defs/


Network Config
--------------

The Makefile can install a networking config file which sets the VM
to use a standard IP address (192.168.56.101).
::
    $ sudo make network-config
    $ sudo reboot

Network config will take effect after the next reboot.


Firewall Rules
--------------

If you want to access Supervisor or Elasticsearch via a web browser,
open ports in the firewall.
::
    $ sudo ufw allow 9001/tcp  # supervisor
    $ sudo ufw allow 9200/tcp  # elasticsearch


VirtualBox Guest Additions
--------------------------

The Makefile can install VirtualBox Guest Additions, which is required
for accessing shared directories on the host system.
::
    $ sudo make vbox-guest

This step requires you to click "Devices > Insert Guest Additions CD
Image" in the device window.


Gitolite keys
-------------

The `ddr` user requires SSL keys in order to synchronize local
collection repositories with those on the main Gitolite server.  Setup
is beyond this INSTALL so please see `ddr-manual`.
