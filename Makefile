PROJECT=ddr
APP=ddrlocal
USER=ddr
SHELL = /bin/bash

APP_VERSION := $(shell cat VERSION)
GIT_SOURCE_URL=https://github.com/densho/ddr-local

# Release name e.g. jessie
DEBIAN_CODENAME := $(shell lsb_release -sc)
# Release numbers e.g. 8.10
DEBIAN_RELEASE := $(shell lsb_release -sr)
# Sortable major version tag e.g. deb8
DEBIAN_RELEASE_TAG = deb$(shell lsb_release -sr | cut -c1)

# current branch name minus dashes or underscores
PACKAGE_BRANCH := $(shell git rev-parse --abbrev-ref HEAD | tr -d _ | tr -d -)
# current commit hash
PACKAGE_COMMIT := $(shell git log -1 --pretty="%h")
# current commit date minus dashes
PACKAGE_TIMESTAMP := $(shell git log -1 --pretty="%ad" --date=short | tr -d -)

PACKAGE_SERVER=ddr.densho.org/static/ddrlocal

SRC_REPO_CMDLN=https://github.com/densho/ddr-cmdln.git
SRC_REPO_LOCAL=https://github.com/densho/ddr-local.git
SRC_REPO_DEFS=https://github.com/densho/ddr-defs.git
SRC_REPO_VOCAB=https://github.com/densho/ddr-vocab.git
SRC_REPO_MANUAL=https://github.com/densho/ddr-manual.git

INSTALL_BASE=/opt
INSTALL_LOCAL=$(INSTALL_BASE)/ddr-local
INSTALL_STATIC=$(INSTALL_LOCAL)/static
INSTALL_CMDLN=$(INSTALL_LOCAL)/ddr-cmdln
INSTALL_DEFS=$(INSTALL_LOCAL)/ddr-defs
INSTALL_VOCAB=$(INSTALL_LOCAL)/ddr-vocab
INSTALL_MANUAL=$(INSTALL_LOCAL)/ddr-manual

VIRTUALENV=$(INSTALL_LOCAL)/venv/ddrlocal
SETTINGS=$(INSTALL_LOCAL)/ddrlocal/ddrlocal/settings.py

CONF_BASE=/etc/ddr
CONF_PRODUCTION=$(CONF_BASE)/ddrlocal.cfg
CONF_LOCAL=$(CONF_BASE)/ddrlocal-local.cfg

SQLITE_BASE=/var/lib/ddr
LOG_BASE=/var/log/ddr

DDR_REPO_BASE=/var/www/media/ddr

MEDIA_BASE=/var/www
MEDIA_ROOT=$(MEDIA_BASE)/media
STATIC_ROOT=$(MEDIA_BASE)/static

OPENJDK_PKG=
ifeq ($(DEBIAN_RELEASE), jessie)
	OPENJDK_PKG=openjdk-7-jre
endif
ifeq ($(DEBIAN_CODENAME), stretch)
	OPENJDK_PKG=openjdk-8-jre
endif

ELASTICSEARCH=elasticsearch-2.4.4.deb
MODERNIZR=modernizr-2.6.2.js
JQUERY=jquery-1.11.0.min.js
BOOTSTRAP=bootstrap-3.1.1-dist
TAGMANAGER=tagmanager-3.0.1
TYPEAHEAD=typeahead-0.10.2
# wget https://download.elastic.co/elasticsearch/elasticsearch/elasticsearch-2.4.4.deb
# wget http://code.jquery.com/jquery-1.11.0.min.js
# wget https://github.com/twbs/bootstrap/releases/download/v3.1.1/bootstrap-3.1.1-dist.zip
# wget https://github.com/max-favilli/tagmanager/archive/v3.0.1.tar.gz
# wget https://github.com/twitter/typeahead.js/archive/v0.10.2.tar.gz

SUPERVISOR_CELERY_CONF=/etc/supervisor/conf.d/celeryd.conf
SUPERVISOR_CELERYBEAT_CONF=/etc/supervisor/conf.d/celerybeat.conf
SUPERVISOR_GUNICORN_CONF=/etc/supervisor/conf.d/ddrlocal.conf
SUPERVISOR_CONF=/etc/supervisor/supervisord.conf
NGINX_CONF=/etc/nginx/sites-available/ddrlocal.conf
NGINX_CONF_LINK=/etc/nginx/sites-enabled/ddrlocal.conf
CGIT_CONF=/etc/cgitrc

DEB_BRANCH := $(shell git rev-parse --abbrev-ref HEAD | tr -d _ | tr -d -)
DEB_ARCH=amd64
DEB_NAME_JESSIE=$(APP)-$(DEB_BRANCH)
DEB_NAME_STRETCH=$(APP)-$(DEB_BRANCH)
# Application version, separator (~), Debian release tag e.g. deb8
# Release tag used because sortable and follows Debian project usage.
DEB_VERSION_JESSIE=$(APP_VERSION)~deb8
DEB_VERSION_STRETCH=$(APP_VERSION)~deb9
DEB_FILE_JESSIE=$(DEB_NAME_JESSIE)_$(DEB_VERSION_JESSIE)_$(DEB_ARCH).deb
DEB_FILE_STRETCH=$(DEB_NAME_STRETCH)_$(DEB_VERSION_STRETCH)_$(DEB_ARCH).deb
DEB_VENDOR=Densho.org
DEB_MAINTAINER=<geoffrey.jost@densho.org>
DEB_DESCRIPTION=Densho Digital Repository editor
DEB_BASE=opt/ddr-local


.PHONY: help


help:
	@echo "--------------------------------------------------------------------------------"
	@echo "ddr-local make commands"
	@echo ""
	@echo "Most commands have subcommands (ex: install-ddr-cmdln, restart-supervisor)"
	@echo ""
	@echo "get     - Clones ddr-local, ddr-cmdln, ddr-defs, wgets static files & ES pkg."
	@echo "install - Performs complete install. See also: make howto-install"
	@echo "reload  - Reloads supervisord and nginx configs"
	@echo "restart - Restarts all daemons"
	@echo "status  - Server status"
	@echo ""
	@echo "vbox-guest     - Installs VirtualBox Guest Additions"
	@echo "network-config - Installs standard network conf (CHANGES IP TO 192.168.56.101!)"
	@echo "get-ddr-defs   - Downloads ddr-defs to $(INSTALL_DEFS)."
	@echo "get-ddr-vocab  - Downloads ddr-vocab to $(INSTALL_VOCAB)."
	@echo "enable-bkgnd   - Enable background processes. (Run make reload on completion)"
	@echo "disable-bkgnd  - Disablebackground processes. (Run make reload on completion)"
	@echo "migrate        - Init/update Django app's database tables."
	@echo "branch BRANCH=[branch] - Switches ddr-local and ddr-cmdln repos to [branch]."
	@echo ""
	@echo "deb       - Makes a DEB package install file."
	@echo "remove    - Removes Debian packages for dependencies."
	@echo "uninstall - Deletes 'compiled' Python files. Leaves build dirs and configs."
	@echo "clean     - Deletes files created while building app, leaves configs."
	@echo ""

howto-install:
	@echo "HOWTO INSTALL"
	@echo "# Basic Debian netinstall"
	@echo "#edit /etc/network/interfaces"
	@echo "#reboot"
	@echo "apt-get update && apt-get upgrade"
	@echo "apt-get install -u openssh ufw"
	@echo "ufw allow 22/tcp"
	@echo "ufw allow 80/tcp"
	@echo "ufw allow 9001/tcp"
	@echo "ufw allow 9200/tcp"
	@echo "ufw enable"
	@echo "apt-get install --assume-yes make"
	@echo "git clone $(SRC_REPO_LOCAL) $(INSTALL_LOCAL)"
	@echo "cd $(INSTALL_LOCAL)/ddrlocal"
	@echo "make install"
	@echo "#make branch BRANCH=develop"
	@echo "#make install"
	@echo "# Place copy of 'ddr' repo in $(DDR_REPO_BASE)/ddr."
	@echo "#make install-defs"
	@echo "#make install-vocab"
	@echo "#make enable-bkgnd"
	@echo "#make migrate"
	@echo "make restart"


get: get-app get-ddr-defs get-ddr-vocab get-elasticsearch get-static

install: install-prep install-daemons install-app install-static install-configs

uninstall: uninstall-app uninstall-configs

clean: clean-app


install-prep: ddr-user install-core git-config install-misc-tools

ddr-user:
	-addgroup --gid=1001 ddr
	-adduser --uid=1001 --gid=1001 --home=/home/ddr --shell=/bin/bash ddr
	-addgroup ddr plugdev
	-addgroup ddr vboxsf
	printf "\n\n# ddrlocal: Activate virtualnv on login\nsource $(VIRTUALENV)/bin/activate\n" >> /home/ddr/.bashrc; \

install-core:
	apt-get --assume-yes install bzip2 curl gdebi-core git-core logrotate ntp p7zip-full wget

git-config:
	git config --global alias.st status
	git config --global alias.co checkout
	git config --global alias.br branch
	git config --global alias.ci commit

install-misc-tools:
	@echo ""
	@echo "Installing miscellaneous tools -----------------------------------------"
	apt-get --assume-yes install ack-grep byobu elinks htop mg multitail


# Copies network config into /etc/network/interfaces
# CHANGES IP ADDRESS TO 192.168.56.101!
network-config:
	@echo ""
	@echo "Configuring network ---------------------------------------------"
	-cp $(INSTALL_LOCAL)/conf/network-interfaces.$(DEBIAN_CODENAME) /etc/network/interfaces
	@echo "/etc/network/interfaces updated."
	@echo "New config will take effect on next reboot."


# Installs VirtualBox Guest Additions and prerequisites
vbox-guest:
	@echo ""
	@echo "Installing VirtualBox Guest Additions ---------------------------"
	@echo "In the VM window, click on \"Devices > Install Guest Additions\"."
	apt-get --quiet install build-essential module-assistant
	m-a prepare
	mount /media/cdrom
	sh /media/cdrom/VBoxLinuxAdditions.run
	-addgroup ddr vboxsf


install-daemons: install-elasticsearch install-redis install-cgit install-nginx

remove-daemons: remove-elasticsearch remove-redis remove-cgit remove-nginx


install-cgit:
	@echo ""
	@echo "cgit ------------------------------------------------------------"
	apt-get --assume-yes install cgit fcgiwrap
	-mkdir /var/www/cgit
	-ln -s /usr/lib/cgit/cgit.cgi /var/www/cgit/cgit.cgi
	-ln -s /usr/share/cgit/cgit.css /var/www/cgit/cgit.css
	-ln -s /usr/share/cgit/favicon.ico /var/www/cgit/favicon.ico
	-ln -s /usr/share/cgit/robots.txt /var/www/cgit/robots.txt

remove-cgit:
	apt-get --assume-yes remove cgit fcgiwrap


install-nginx:
	@echo ""
	@echo "Nginx ------------------------------------------------------------------"
	apt-get --assume-yes remove apache2
	apt-get --assume-yes install nginx

remove-nginx:
	apt-get --assume-yes remove nginx

install-redis:
	@echo ""
	@echo "Redis ------------------------------------------------------------------"
	apt-get --assume-yes install redis-server

remove-redis:
	apt-get --assume-yes remove redis-server


get-elasticsearch:
	wget -nc -P /tmp/downloads http://$(PACKAGE_SERVER)/$(ELASTICSEARCH)

install-elasticsearch: install-core
	@echo ""
	@echo "Elasticsearch ----------------------------------------------------------"
# Elasticsearch is configured/restarted here so it's online by the time script is done.
	apt-get --assume-yes install $(OPENJDK_PKG)
	-gdebi --non-interactive /tmp/downloads/$(ELASTICSEARCH)
#cp $(INSTALL_BASE)/ddr-public/conf/elasticsearch.yml /etc/elasticsearch/
#chown root.root /etc/elasticsearch/elasticsearch.yml
#chmod 644 /etc/elasticsearch/elasticsearch.yml
# 	@echo "${bldgrn}search engine (re)start${txtrst}"
	-service elasticsearch stop
	-systemctl disable elasticsearch.service

enable-elasticsearch:
	systemctl enable elasticsearch.service

disable-elasticsearch:
	systemctl disable elasticsearch.service

remove-elasticsearch:
	apt-get --assume-yes remove $(OPENJDK_PKG) elasticsearch


install-virtualenv:
	@echo ""
	@echo "install-virtualenv -----------------------------------------------------"
	apt-get --assume-yes install python-six python-pip python-virtualenv python-dev
	test -d $(VIRTUALENV) || virtualenv --distribute --setuptools $(VIRTUALENV)
	source $(VIRTUALENV)/bin/activate; \
	pip install -U bpython appdirs blessings curtsies greenlet packaging pygments pyparsing setuptools wcwidth
#	virtualenv --relocatable $(VIRTUALENV)  # Make venv relocatable


install-dependencies: install-core install-misc-tools install-daemons install-git-annex
	@echo ""
	@echo "install-dependencies ---------------------------------------------------"
	apt-get --assume-yes install python-pip python-virtualenv
	apt-get --assume-yes install python-dev
	apt-get --assume-yes install git-core git-annex libxml2-dev libxslt1-dev libz-dev pmount udisks2
	apt-get --assume-yes install imagemagick libexempi3 libssl-dev python-dev libxml2 libxml2-dev libxslt1-dev supervisor

mkdirs: mkdir-ddr-cmdln mkdir-ddr-local


get-app: get-ddr-cmdln get-ddr-local get-ddr-manual

install-app: install-git-annex install-virtualenv install-ddr-cmdln install-ddr-local install-configs install-daemon-configs

uninstall-app: uninstall-ddr-cmdln uninstall-ddr-local uninstall-ddr-manual uninstall-configs uninstall-daemon-configs

clean-app: clean-ddr-cmdln clean-ddr-local clean-ddr-manual


install-git-annex:
	apt-get --assume-yes install git-core git-annex

get-ddr-cmdln:
	@echo ""
	@echo "get-ddr-cmdln ----------------------------------------------------------"
	git status | grep "On branch"
	if test -d $(INSTALL_CMDLN); \
	then cd $(INSTALL_CMDLN) && git pull; \
	else cd $(INSTALL_LOCAL) && git clone $(SRC_REPO_CMDLN); \
	fi

setup-ddr-cmdln:
	git status | grep "On branch"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_CMDLN)/ddr && python setup.py install

install-ddr-cmdln: install-virtualenv mkdir-ddr-cmdln
	@echo ""
	@echo "install-ddr-cmdln ------------------------------------------------------"
	git status | grep "On branch"
	apt-get --assume-yes install git-core git-annex libxml2-dev libxslt1-dev libz-dev pmount udisks2
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_CMDLN)/ddr && python setup.py install
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_CMDLN)/ddr && pip install -U -r $(INSTALL_CMDLN)/ddr/requirements/production.txt

mkdir-ddr-cmdln:
	@echo ""
	@echo "mkdir-ddr-cmdln --------------------------------------------------------"
	-mkdir $(LOG_BASE)
	chown -R ddr.root $(LOG_BASE)
	chmod -R 755 $(LOG_BASE)
	-mkdir -p $(MEDIA_ROOT)
	chown -R ddr.root $(MEDIA_ROOT)
	chmod -R 755 $(MEDIA_ROOT)

uninstall-ddr-cmdln: install-virtualenv
	@echo ""
	@echo "uninstall-ddr-cmdln ----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_CMDLN)/ddr && pip uninstall -y -r $(INSTALL_CMDLN)/ddr/requirements/production.txt

clean-ddr-cmdln:
	-rm -Rf $(INSTALL_CMDLN)/ddr/build
	-rm -Rf $(INSTALL_CMDLN)/ddr/ddr_cmdln.egg-info
	-rm -Rf $(INSTALL_CMDLN)/ddr/dist


get-ddr-local:
	@echo ""
	@echo "get-ddr-local ----------------------------------------------------------"
	git status | grep "On branch"
	git pull

install-ddr-local: install-virtualenv mkdir-ddr-local
	@echo ""
	@echo "install-ddr-local ------------------------------------------------------"
	git status | grep "On branch"
	apt-get --assume-yes install imagemagick libexempi3 libssl-dev python-dev libxml2 libxml2-dev libxslt1-dev supervisor
	source $(VIRTUALENV)/bin/activate; \
	pip install -U -r $(INSTALL_LOCAL)/requirements.txt

mkdir-ddr-local:
	@echo ""
	@echo "mkdir-ddr-local --------------------------------------------------------"
# logs dir
	-mkdir $(LOG_BASE)
	chown -R ddr.root $(LOG_BASE)
	chmod -R 755 $(LOG_BASE)
# sqlite db dir
	-mkdir $(SQLITE_BASE)
	chown -R ddr.root $(SQLITE_BASE)
	chmod -R 755 $(SQLITE_BASE)
# media dir
	-mkdir -p $(MEDIA_ROOT)
	chown -R ddr.root $(MEDIA_ROOT)
	chmod -R 755 $(MEDIA_ROOT)
# static dir
	-mkdir -p $(STATIC_ROOT)
	chown -R ddr.root $(STATIC_ROOT)
	chmod -R 755 $(STATIC_ROOT)

uninstall-ddr-local: install-virtualenv
	@echo ""
	@echo "uninstall-ddr-local ----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_LOCAL)/ddrlocal && pip uninstall -y -r $(INSTALL_LOCAL)/requirements.txt

clean-ddr-local:
	-rm -Rf $(VIRTUALENV)
	-rm -Rf $(INSTALL_LOCAL)/*.deb


get-ddr-defs:
	@echo ""
	@echo "get-ddr-defs -----------------------------------------------------------"
	git status | grep "On branch"
	if test -d $(INSTALL_DEFS); \
	then cd $(INSTALL_DEFS) && git pull; \
	else cd $(INSTALL_LOCAL) && git clone $(SRC_REPO_DEFS) $(INSTALL_DEFS); \
	fi


get-ddr-vocab:
	@echo ""
	@echo "get-ddr-vocab ----------------------------------------------------------"
	git status | grep "On branch"
	if test -d $(INSTALL_VOCAB); \
	then cd $(INSTALL_VOCAB) && git pull; \
	else cd $(INSTALL_LOCAL) && git clone $(SRC_REPO_VOCAB) $(INSTALL_VOCAB); \
	fi


migrate:
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_LOCAL)/ddrlocal && ./manage.py migrate --noinput
	chown -R ddr.root $(SQLITE_BASE)
	chmod -R 750 $(SQLITE_BASE)
	chown -R ddr.root $(LOG_BASE)
	chmod -R 755 $(LOG_BASE)

branch:
	cd $(INSTALL_LOCAL)/ddrlocal; python ./bin/git-checkout-branch.py $(BRANCH)


get-static: get-modernizr get-bootstrap get-jquery get-tagmanager get-typeahead

get-modernizr:
	@echo ""
	@echo "Modernizr --------------------------------------------------------------"
	mkdir -p $(INSTALL_STATIC)/js/
	wget -nc -P $(INSTALL_STATIC)/js http://$(PACKAGE_SERVER)/$(MODERNIZR)

get-bootstrap:
	@echo ""
	@echo "Bootstrap --------------------------------------------------------------"
	mkdir -p $(INSTALL_STATIC)/
	wget -nc -P $(INSTALL_STATIC) http://$(PACKAGE_SERVER)/$(BOOTSTRAP).zip
	7z x -y -o$(INSTALL_STATIC) $(INSTALL_STATIC)/$(BOOTSTRAP).zip
	-rm $(INSTALL_STATIC)/$(BOOTSTRAP).zip

get-jquery:
	@echo ""
	@echo "jQuery -----------------------------------------------------------------"
	mkdir -p $(INSTALL_STATIC)/js/
	wget -nc -P $(INSTALL_STATIC)/js http://$(PACKAGE_SERVER)/$(JQUERY)

get-tagmanager:
	@echo ""
	@echo "tagmanager -------------------------------------------------------------"
	mkdir -p $(INSTALL_STATIC)/
	wget -nc -P $(INSTALL_STATIC)/ http://$(PACKAGE_SERVER)/$(TAGMANAGER).tgz
	cd $(INSTALL_STATIC)/ && tar xzf $(INSTALL_STATIC)/$(TAGMANAGER).tgz
	-rm $(INSTALL_STATIC)/$(TAGMANAGER).tgz

get-typeahead:
	@echo ""
	@echo "typeahead --------------------------------------------------------------"
	mkdir -p $(INSTALL_STATIC)/
	wget -nc -P $(INSTALL_STATIC)/ http://$(PACKAGE_SERVER)/$(TYPEAHEAD).tgz
	cd $(INSTALL_STATIC)/ && tar xzf $(INSTALL_STATIC)/$(TYPEAHEAD).tgz
	-rm $(INSTALL_STATIC)/$(TYPEAHEAD).tgz

install-static:
	@echo ""
	@echo "install-static ---------------------------------------------------------"
	mkdir -p $(STATIC_ROOT)/
	cp -R $(INSTALL_STATIC)/* $(STATIC_ROOT)/
	chown -R root.root $(STATIC_ROOT)/
	-ln -s $(STATIC_ROOT)/js/$(MODERNIZR) $(STATIC_ROOT)/js/modernizr.js
	-ln -s $(STATIC_ROOT)/$(BOOTSTRAP) $(STATIC_ROOT)/bootstrap
	-ln -s $(STATIC_ROOT)/js/$(JQUERY) $(STATIC_ROOT)/js/jquery.js
	-ln -s $(STATIC_ROOT)/$(TAGMANAGER) $(STATIC_ROOT)/js/tagmanager
	-ln -s $(STATIC_ROOT)/$(TYPEAHEAD) $(STATIC_ROOT)/js/typeahead

clean-static:
	-rm -Rf $(STATIC_ROOT)/
	-rm -Rf $(INSTALL_STATIC)/*


install-configs:
	@echo ""
	@echo "configuring ddr-local --------------------------------------------------"
# base settings file
	-mkdir /etc/ddr
	cp $(INSTALL_LOCAL)/conf/ddrlocal.cfg $(CONF_PRODUCTION)
	chown root.root $(CONF_PRODUCTION)
	chmod 644 $(CONF_PRODUCTION)
	touch $(CONF_LOCAL)
	chown ddr.root $(CONF_LOCAL)
	chmod 640 $(CONF_LOCAL)
# web app settings
	cp $(INSTALL_LOCAL)/conf/settings.py $(SETTINGS)
	chown root.root $(SETTINGS)
	chmod 644 $(SETTINGS)

uninstall-configs:
	-rm $(SETTINGS)
	-rm $(CONF_PRODUCTION)


install-daemon-configs:
	@echo ""
	@echo "install-daemon-configs -------------------------------------------------"
# nginx settings
	cp $(INSTALL_LOCAL)/conf/nginx.conf $(NGINX_CONF)
	chown root.root $(NGINX_CONF)
	chmod 644 $(NGINX_CONF)
	-ln -s $(NGINX_CONF) $(NGINX_CONF_LINK)
	-rm /etc/nginx/sites-enabled/default
# supervisord
	cp $(INSTALL_LOCAL)/conf/celeryd.conf $(SUPERVISOR_CELERY_CONF)
	cp $(INSTALL_LOCAL)/conf/supervisor.conf $(SUPERVISOR_GUNICORN_CONF)
	cp $(INSTALL_LOCAL)/conf/supervisord.conf $(SUPERVISOR_CONF)
	chown root.root $(SUPERVISOR_CELERY_CONF)
	chown root.root $(SUPERVISOR_GUNICORN_CONF)
	chown root.root $(SUPERVISOR_CONF)
	chmod 644 $(SUPERVISOR_CELERY_CONF)
	chmod 644 $(SUPERVISOR_GUNICORN_CONF)
	chmod 644 $(SUPERVISOR_CONF)
# cgitrc
	cp $(INSTALL_LOCAL)/conf/cgitrc $(CGIT_CONF)

uninstall-daemon-configs:
	-rm $(NGINX_CONF)
	-rm $(NGINX_CONF_LINK)
	-rm $(SUPERVISOR_CELERY_CONF)
	-rm $(SUPERVISOR_CONF)


enable-bkgnd:
	cp $(INSTALL_LOCAL)/conf/celerybeat.conf $(SUPERVISOR_CELERYBEAT_CONF)
	chown root.root $(SUPERVISOR_CELERYBEAT_CONF)
	chmod 644 $(SUPERVISOR_CELERYBEAT_CONF)

disable-bkgnd:
	-rm $(SUPERVISOR_CELERYBEAT_CONF)


reload: reload-nginx reload-supervisor

reload-nginx:
	sudo service nginx reload

reload-supervisor:
	supervisorctl reload

reload-app: reload-supervisor


stop: stop-elasticsearch stop-redis stop-cgit stop-nginx stop-supervisor

stop-elasticsearch:
	-service elasticsearch stop

stop-redis:
	-service redis-server stop

stop-cgit:
	-service fcgiwrap stop

stop-nginx:
	-service nginx stop

stop-supervisor:
	-service supervisor stop

stop-app: stop-supervisor


restart: restart-supervisor restart-redis restart-cgit restart-nginx

restart-elasticsearch:
	-service elasticsearch restart

restart-redis:
	-service redis-server restart

restart-cgit:
	-service fcgiwrap restart

restart-nginx:
	-service nginx restart

restart-supervisor:
	-service supervisor stop
	-service supervisor start

restart-app: restart-supervisor


# just Redis and Supervisor
restart-minimal: stop-elasticsearch restart-redis stop-nginx restart-supervisor


status:
	@echo "------------------------------------------------------------------------"
	-systemctl status elasticsearch
	@echo " - - - - -"
	-systemctl status redis-server
	@echo " - - - - -"
	-systemctl status nginx
	@echo " - - - - -"
	-systemctl status supervisor
	-supervisorctl status
	@echo " - - - - -"
	-git annex version | grep version
	@echo " - - - - -"
	-uptime
	@echo ""

git-status:
	@echo "------------------------------------------------------------------------"
	cd $(INSTALL_CMDLN) && git status
	@echo "------------------------------------------------------------------------"
	cd $(INSTALL_LOCAL) && git status


get-ddr-manual:
	@echo ""
	@echo "get-ddr-manual ---------------------------------------------------------"
	git status | grep "On branch"
	if test -d $(INSTALL_MANUAL); \
	then cd $(INSTALL_MANUAL) && git pull; \
	else cd $(INSTALL_LOCAL) && git clone $(SRC_REPO_MANUAL); \
	fi

install-ddr-manual: install-virtualenv
	@echo ""
	@echo "install-ddr-manual -----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	pip install -U sphinx
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_MANUAL) && make html
	rm -Rf $(MEDIA_ROOT)/manual
	mv $(INSTALL_MANUAL)/build/html $(MEDIA_ROOT)/manual

uninstall-ddr-manual:
	pip uninstall -y sphinx

clean-ddr-manual:
	-rm -Rf $(INSTALL_MANUAL)/build


# http://fpm.readthedocs.io/en/latest/
# https://stackoverflow.com/questions/32094205/set-a-custom-install-directory-when-making-a-deb-package-with-fpm
# https://brejoc.com/tag/fpm/
deb: deb-jessie deb-stretch

# deb-jessie and deb-stretch are identical EXCEPT:
# jessie: --depends openjdk-7-jre
# stretch: --depends openjdk-7-jre
deb-jessie:
	@echo ""
	@echo "FPM packaging (jessie) -------------------------------------------------"
	-rm -Rf $(DEB_FILE_JESSIE)
	virtualenv --relocatable $(VIRTUALENV)  # Make venv relocatable
	fpm   \
	--verbose   \
	--input-type dir   \
	--output-type deb   \
	--name $(DEB_NAME_JESSIE)   \
	--version $(DEB_VERSION_JESSIE)   \
	--package $(DEB_FILE_JESSIE)  \
	--url "$(GIT_SOURCE_URL)"   \
	--vendor "$(DEB_VENDOR)"   \
	--maintainer "$(DEB_MAINTAINER)"   \
	--description "$(DEB_DESCRIPTION)"   \
	--depends "nginx-light"   \
	--depends "cgit"   \
	--depends "fcgiwrap"   \
	--depends "gdebi-core"   \
	--depends "git-annex"   \
	--depends "git-core"   \
	--depends "imagemagick"   \
	--depends "libexempi3"   \
	--depends "libssl-dev"   \
	--depends "libwww-perl"   \
	--depends "libxml2"   \
	--depends "libxml2-dev"   \
	--depends "libxslt1-dev"   \
	--depends "libz-dev"   \
	--depends "munin"   \
	--depends "munin-node"   \
	--depends "openjdk-7-jre"   \
	--depends "pmount"   \
	--depends "python-dev"   \
	--depends "python-pip"   \
	--depends "python-six"   \
	--depends "python-virtualenv"   \
	--depends "redis-server"   \
	--depends "supervisor"   \
	--depends "udisks2"   \
	--after-install "bin/after-install.sh"   \
	--chdir $(INSTALL_LOCAL)   \
	conf/ddrlocal.cfg=etc/ddr/ddrlocal.cfg   \
	conf/celeryd.conf=etc/supervisor/conf.d/celeryd.conf   \
	conf/supervisor.conf=etc/supervisor/conf.d/ddrlocal.conf   \
	conf/nginx.conf=etc/nginx/sites-available/ddrlocal.conf   \
	conf/README-logs=$(LOG_BASE)/README  \
	conf/README-sqlite=$(SQLITE_BASE)/README  \
	conf/README-media=$(MEDIA_ROOT)/README  \
	conf/README-static=$(STATIC_ROOT)/README  \
	static=var/www   \
	bin=$(DEB_BASE)   \
	conf=$(DEB_BASE)   \
	COPYRIGHT=$(DEB_BASE)   \
	ddr-cmdln=$(DEB_BASE)   \
	ddr-defs=$(DEB_BASE)   \
	ddr-vocab=$(DEB_BASE)   \
	ddrlocal=$(DEB_BASE)   \
	.git=$(DEB_BASE)   \
	.gitignore=$(DEB_BASE)   \
	INSTALL.rst=$(DEB_BASE)   \
	LICENSE=$(DEB_BASE)   \
	Makefile=$(DEB_BASE)   \
	README.rst=$(DEB_BASE)   \
	static=$(DEB_BASE)   \
	venv=$(DEB_BASE)   \
	VERSION=$(DEB_BASE)

# deb-jessie and deb-stretch are identical EXCEPT:
# jessie: --depends openjdk-7-jre
# stretch: --depends openjdk-7-jre
deb-stretch:
	@echo ""
	@echo "FPM packaging (stretch) ------------------------------------------------"
	-rm -Rf $(DEB_FILE_STRETCH)
	virtualenv --relocatable $(VIRTUALENV)  # Make venv relocatable
	fpm   \
	--verbose   \
	--input-type dir   \
	--output-type deb   \
	--name $(DEB_NAME_STRETCH)   \
	--version $(DEB_VERSION_STRETCH)   \
	--package $(DEB_FILE_STRETCH)   \
	--url "$(GIT_SOURCE_URL)"   \
	--vendor "$(DEB_VENDOR)"   \
	--maintainer "$(DEB_MAINTAINER)"   \
	--description "$(DEB_DESCRIPTION)"   \
	--depends "nginx-light"   \
	--depends "cgit"   \
	--depends "fcgiwrap"   \
	--depends "gdebi-core"   \
	--depends "git-annex"   \
	--depends "git-core"   \
	--depends "imagemagick"   \
	--depends "libexempi3"   \
	--depends "libssl-dev"   \
	--depends "libwww-perl"   \
	--depends "libxml2"   \
	--depends "libxml2-dev"   \
	--depends "libxslt1-dev"   \
	--depends "libz-dev"   \
	--depends "munin"   \
	--depends "munin-node"   \
	--depends "openjdk-8-jre"   \
	--depends "pmount"   \
	--depends "python-dev"   \
	--depends "python-pip"   \
	--depends "python-six"   \
	--depends "python-virtualenv"   \
	--depends "redis-server"   \
	--depends "supervisor"   \
	--depends "udisks2"   \
	--after-install "bin/after-install.sh"   \
	--chdir $(INSTALL_LOCAL)   \
	conf/ddrlocal.cfg=etc/ddr/ddrlocal.cfg   \
	conf/celeryd.conf=etc/supervisor/conf.d/celeryd.conf   \
	conf/supervisor.conf=etc/supervisor/conf.d/ddrlocal.conf   \
	conf/nginx.conf=etc/nginx/sites-available/ddrlocal.conf   \
	conf/logrotate=etc/logrotate.d/ddr   \
	conf/README-logs=$(LOG_BASE)/README  \
	conf/README-sqlite=$(SQLITE_BASE)/README  \
	conf/README-media=$(MEDIA_ROOT)/README  \
	conf/README-static=$(STATIC_ROOT)/README  \
	static=var/www   \
	bin=$(DEB_BASE)   \
	conf=$(DEB_BASE)   \
	COPYRIGHT=$(DEB_BASE)   \
	ddr-cmdln=$(DEB_BASE)   \
	ddr-defs=$(DEB_BASE)   \
	ddr-vocab=$(DEB_BASE)   \
	ddrlocal=$(DEB_BASE)   \
	.git=$(DEB_BASE)   \
	.gitignore=$(DEB_BASE)   \
	INSTALL.rst=$(DEB_BASE)   \
	LICENSE=$(DEB_BASE)   \
	Makefile=$(DEB_BASE)   \
	README.rst=$(DEB_BASE)   \
	static=$(DEB_BASE)   \
	venv=$(DEB_BASE)   \
	VERSION=$(DEB_BASE)
