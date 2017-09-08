INSTALL
=======

For more complete instructions, see the "Admins/Workstations" section
in `ddr-manual <https://github.com/densho/ddr-manual/>`_.

The `ddr-local` install and update scripts below have been tested on
Debian 8.0 running as a VM in VirtualBox.


Package File
------------

You can install directly from a `ddrlocal-BRANCH_VERSION_ARCH.deb`
file.  Debian packaged dependencies (Nginx, Redis, etc) are
automatically installed as required.
::
    # gdebi ddrlocal-BRANCH_VERSION_ARCH.deb
    ...

This method is similar in effect to installing from source (i.e. the
Git repository) but is faster (you don't have to build the software)
and lets you completely remove the install if you so choose.  Note
that you will not receive automatic updates from the repository.

After the install completes you can use `make` commands to manage the
installation.


Debian Repository
-----------------

Using one of our Debian repositories is the recommended way to install
`ddr-local`, since it makes updates and upgrades quick and easy.

**Adding the Repository**

To use our repository you must first add the packaging signing key
using the `apt-key` tool and then add the repository itself to your
list of APT sources. Commands for accomplishing this are listed below
(for completeness we include commands to install curl and the apt
tools - you may already have these installed).
::
    # apt-get update && apt-get install curl apt-transport-https gnupg
    ...
    # curl -s http://packages.densho.org/debian/keys/archive.asc |apt-key add -
    ...
    # echo "deb http://packages.densho.org/debian/ master main" |tee /etc/apt/sources.list.d/packages_densho_org_debian.list
    ...

**Installing the Package**

You can now install the DDR Editor with a single command:
::
    # apt-get update && apt-get install ddrlocal-master
    ...

If you wish to use the develop branch instead of the master branch,
remove `ddrlocal-master` and install `ddrlocal-develop`.  Switching
branches in a package install is not recommended, as updates will
probably damage your install.  If you want to switch branches you
should consider a source install.

Now you should be able to run mailpile on the command line and join
the fun! If you have installed the Apache integration, you can access
https://your.example.com/mailpile/ and log on that way.


Uninstalling
------------

A normal `apt-get remove` uninstalls the software from your system,
leaving config and data files in place.
::
    # apt-get remove ddrlocal-master
    ...

To completely remove all files installed as part of `ddr-local`
(e.g. configs, static, and media files), use `apt-get purge`.
IMPORTANT: this removes the `/media/` directory which contains your
data!
::
    # apt-get purge ddrlocal-master
    ...
    # rm /etc/apt/sources.list.d/packages_densho_org_debian.list && apt-get update
    ...


Installing From Source
----------------------

Technically you can clone `ddr-local` anywhere you want.  You can also
build the project manually but it's much easier to use `make install`.
When you run `make install` it will attempt to install the app in
`/opt/ddr-local`, so you might as well just clone it to that location.
::
    # apt-get update && apt-get upgrade
    # apt-get install git
    # git clone https://github.com/densho/ddr-local.git /opt/ddr-local
    $ cd /opt/ddr-local/

Git-cloning and downloading static files are a separate step from the
actual installation.  GitHub may ask you for passwords.
::
    # make get

This step installs dependencies from Debian packages, installs Python
dependencies in a virtualenv, and places static assets and config
files in their places.
::
    # make install

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


Gitolite keys
-------------

The `ddr` user requires SSL keys in order to synchronize local
collection repositories with those on the main Gitolite server.  Setup
is beyond this INSTALL so please see `ddr-manual`.


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


Firewall Rules
--------------

If you want to access Supervisor or Elasticsearch via a web browser,
open ports in the firewall.
::
    $ sudo ufw allow 9001/tcp  # supervisor
    $ sudo ufw allow 9200/tcp  # elasticsearch
