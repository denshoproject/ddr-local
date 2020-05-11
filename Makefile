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

ifeq ($(DEBIAN_CODENAME), stretch)
	PYTHON_VERSION=3.5
endif
ifeq ($(DEBIAN_CODENAME), buster)
	PYTHON_VERSION=3.7
endif

# current branch name minus dashes or underscores
PACKAGE_BRANCH := $(shell git rev-parse --abbrev-ref HEAD | tr -d _ | tr -d -)
# current commit hash
PACKAGE_COMMIT := $(shell git log -1 --pretty="%h")
# current commit date minus dashes
PACKAGE_TIMESTAMP := $(shell git log -1 --pretty="%ad" --date=short | tr -d -)

PACKAGE_SERVER=ddr.densho.org/static/ddrlocal

SRC_REPO_CMDLN=https://github.com/densho/ddr-cmdln.git
SRC_REPO_CMDLN_ASSETS=https://github.com/densho/ddr-cmdln-assets.git
SRC_REPO_LOCAL=https://github.com/densho/ddr-local.git
SRC_REPO_DEFS=https://github.com/densho/ddr-defs.git
SRC_REPO_VOCAB=https://github.com/densho/densho-vocab.git
SRC_REPO_MANUAL=https://github.com/densho/ddr-manual.git

INSTALL_BASE=/opt
INSTALLDIR=$(INSTALL_BASE)/ddr-cmdln
REQUIREMENTS=$(INSTALLDIR)/requirements.txt
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache

CWD := $(shell pwd)
INSTALL_LOCAL=$(CWD)
INSTALL_STATIC=$(INSTALL_LOCAL)/static
INSTALL_CMDLN=$(INSTALL_LOCAL)/ddr-cmdln
INSTALL_CMDLN_ASSETS=$(INSTALL_CMDLN)/ddr-cmdln-assets
INSTALL_DEFS=$(INSTALL_LOCAL)/ddr-defs
INSTALL_VOCAB=$(INSTALL_LOCAL)/densho-vocab
INSTALL_MANUAL=$(INSTALL_LOCAL)/ddr-manual

COMMIT_LOCAL := $(shell git -C $(INSTALL_LOCAL) log --decorate --abbrev-commit --pretty=oneline -1)
COMMIT_CMDLN := $(shell git -C $(INSTALL_CMDLN) log --decorate --abbrev-commit --pretty=oneline -1)
COMMIT_DEFS := $(shell git -C $(INSTALL_DEFS) log --decorate --abbrev-commit --pretty=oneline -1)
COMMIT_VOCAB := $(shell git -C $(INSTALL_VOCAB) log --decorate --abbrev-commit --pretty=oneline -1)

VIRTUALENV=$(INSTALL_LOCAL)/venv/ddrlocal

CONF_BASE=/etc/ddr
CONF_PRODUCTION=$(CONF_BASE)/ddrlocal.cfg
CONF_LOCAL=$(CONF_BASE)/ddrlocal-local.cfg

SQLITE_BASE=/var/lib/ddr
LOG_BASE=/var/log/ddr

DDR_REPO_BASE=/var/www/media/ddr

MEDIA_BASE=/var/www
MEDIA_ROOT=$(MEDIA_BASE)/media
STATIC_ROOT=$(MEDIA_BASE)/static

LIBEXEMPI3_PKG=
ifeq ($(DEBIAN_CODENAME), stretch)
	LIBEXEMPI3_PKG=libexempi3
endif
ifeq ($(DEBIAN_CODENAME), buster)
	LIBEXEMPI3_PKG=libexempi8
endif

OPENJDK_PKG=
ifeq ($(DEBIAN_CODENAME), stretch)
	OPENJDK_PKG=openjdk-8-jre
endif
ifeq ($(DEBIAN_CODENAME), buster)
	OPENJDK_PKG=openjdk-11-jre
endif

ELASTICSEARCH=elasticsearch-7.3.1-amd64.deb
MODERNIZR=modernizr-2.6.2.js
JQUERY=jquery-1.11.0.min.js
BOOTSTRAP=bootstrap-3.1.1-dist
TAGMANAGER=tagmanager-3.0.1
TYPEAHEAD=typeahead-0.10.2
# wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-7.3.1.deb
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

TGZ_BRANCH := $(shell python3 bin/package-branch.py)
TGZ_FILE=$(APP)_$(APP_VERSION)
TGZ_DIR=$(INSTALL_LOCAL)/$(TGZ_FILE)
TGZ_CMDLN=$(TGZ_DIR)/ddr-cmdln
TGZ_CMDLN_ASSETS=$(TGZ_DIR)/ddr-cmdln/ddr-cmdln-assets
TGZ_DEFS=$(TGZ_DIR)/ddr-defs
TGZ_VOCAB=$(TGZ_DIR)/densho-vocab
TGZ_MANUAL=$(TGZ_DIR)/ddr-manual
TGZ_STATIC=$(TGZ_DIR)/static

# Adding '-rcN' to VERSION will name the package "ddrlocal-release"
# instead of "ddrlocal-BRANCH"
DEB_BRANCH := $(shell python3 bin/package-branch.py)
DEB_ARCH=amd64
DEB_NAME_JESSIE=$(APP)-$(DEB_BRANCH)
DEB_NAME_STRETCH=$(APP)-$(DEB_BRANCH)
DEB_NAME_BUSTER=$(APP)-$(DEB_BRANCH)
# Application version, separator (~), Debian release tag e.g. deb8
# Release tag used because sortable and follows Debian project usage.
DEB_VERSION_JESSIE=$(APP_VERSION)~deb8
DEB_VERSION_STRETCH=$(APP_VERSION)~deb9
DEB_VERSION_BUSTER=$(APP_VERSION)~deb10
DEB_FILE_JESSIE=$(DEB_NAME_JESSIE)_$(DEB_VERSION_JESSIE)_$(DEB_ARCH).deb
DEB_FILE_STRETCH=$(DEB_NAME_STRETCH)_$(DEB_VERSION_STRETCH)_$(DEB_ARCH).deb
DEB_FILE_BUSTER=$(DEB_NAME_BUSTER)_$(DEB_VERSION_BUSTER)_$(DEB_ARCH).deb
DEB_VENDOR=Densho.org
DEB_MAINTAINER=<geoffrey.jost@densho.org>
DEB_DESCRIPTION=Densho Digital Repository editor
DEB_BASE=opt/ddr-local


debug:
	@echo "ddr-local: $(COMMIT_LOCAL)"
	@echo "ddr-cmdln: $(COMMIT_CMDLN)"
	@echo "ddr-defs:  $(COMMIT_DEFS)"
	@echo "densho-vocab: $(COMMIT_VOCAB)"


.PHONY: help


help:
	@echo "--------------------------------------------------------------------------------"
	@echo "ddr-local make commands"
	@echo ""
	@echo "Most commands have subcommands (ex: install-ddr-cmdln, restart-supervisor)"
	@echo ""
	@echo "get     - Clones ddr-local, ddr-cmdln, ddr-defs, wgets static files & ES pkg."
	@echo "install - Performs complete install. See also: make howto-install"
	@echo "test    - Run unit tests"
	@echo ""
	@echo "vbox-guest     - Installs VirtualBox Guest Additions"
	@echo "network-config - Installs standard network conf (CHANGES IP TO 192.168.56.101!)"
	@echo "get-ddr-defs   - Downloads ddr-defs to $(INSTALL_DEFS)."
	@echo "get-densho-vocab - Downloads densho-vocab to $(INSTALL_VOCAB)."
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


get: get-app get-ddr-defs get-densho-vocab get-elasticsearch get-static

install: install-prep install-daemons install-app install-static install-configs

test: test-app

coverage: coverage-app

uninstall: uninstall-app uninstall-configs

clean: clean-app


install-prep: ddr-user install-core git-config install-misc-tools

ddr-user:
	-addgroup --gid=1001 ddr
	-adduser --uid=1001 --gid=1001 --home=/home/ddr --shell=/bin/bash --disabled-login --gecos "" ddr
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


install-daemons: install-supervisor install-redis install-nginx install-cgit install-elasticsearch

remove-daemons: remove-supervisor remove-redis remove-nginx remove-cgit remove-elasticsearch


install-supervisor:
	@echo ""
	@echo "Supervisord ------------------------------------------------------------"
	apt-get --assume-yes install supervisor

remove-supervisor:
	apt-get --assume-yes remove supervisor


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
	apt-get --assume-yes install nginx-light

remove-nginx:
	apt-get --assume-yes remove nginx-light

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
#cp $(INSTALL_LOCAL)/conf/elasticsearch.yml /etc/elasticsearch/
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
	apt-get --assume-yes install python3-pip python3-venv
	python3 -m venv $(VIRTUALENV)

install-setuptools: install-virtualenv
	@echo ""
	@echo "install-setuptools -----------------------------------------------------"
	apt-get --assume-yes install python3-dev
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U --cache-dir=$(PIP_CACHE_DIR) setuptools


install-dependencies: install-core install-misc-tools install-daemons
	@echo ""
	@echo "install-dependencies ---------------------------------------------------"
	apt-get --assume-yes install python3-dev python3-pip python3-venv
	apt-get --assume-yes install git-core git-annex libxml2-dev libxslt1-dev libz-dev pmount udisks2
	apt-get --assume-yes install imagemagick libssl-dev libxml2 libxml2-dev libxslt1-dev
	apt-get --assume-yes install $(LIBEXEMPI3_PKG)

mkdirs: mkdir-ddr-cmdln mkdir-ddr-local


get-app: get-ddr-cmdln get-ddr-local get-ddr-manual

pip-download: pip-download-cmdln pip-download-local

install-app: install-dependencies install-setuptools install-ddr-cmdln install-ddr-local install-configs install-daemon-configs

test-app: test-ddr-cmdln test-ddr-local

coverage-app: coverage-ddr-cmdln

uninstall-app: uninstall-ddr-cmdln uninstall-ddr-local uninstall-ddr-manual uninstall-configs uninstall-daemon-configs

clean-app: clean-ddr-cmdln clean-ddr-local clean-ddr-manual


get-ddr-cmdln:
	@echo ""
	@echo "get-ddr-cmdln ----------------------------------------------------------"
	git status | grep "On branch"
	if test -d $(INSTALL_CMDLN); \
	then cd $(INSTALL_CMDLN) && git pull; \
	else git clone $(SRC_REPO_CMDLN); \
	fi

get-ddr-cmdln-assets:
	@echo ""
	@echo "get-ddr-cmdln-assets ---------------------------------------------------"
	if test -d $(INSTALL_CMDLN_ASSETS); \
	then cd $(INSTALL_CMDLN_ASSETS) && git pull; \
	else git clone $(SRC_REPO_CMDLN_ASSETS); \
	fi

setup-ddr-cmdln:
	git status | grep "On branch"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_CMDLN)/ddr; python setup.py install

pip-download-cmdln:
	source $(VIRTUALENV)/bin/activate; \
	pip download --no-binary=:all: --destination-directory=$(INSTALL_CMDLN)/vendor -r $(INSTALL_CMDLN)/requirements.txt

install-ddr-cmdln: install-setuptools
	@echo ""
	@echo "install-ddr-cmdln ------------------------------------------------------"
	git status | grep "On branch"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_CMDLN)/ddr; python setup.py install
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U --cache-dir=$(PIP_CACHE_DIR) -r $(INSTALL_CMDLN)/requirements.txt
	-mkdir -p /etc/ImageMagick-6/
	cp $(INSTALL_CMDLN)/conf/imagemagick-policy.xml /etc/ImageMagick-6/policy.xml

mkdir-ddr-cmdln:
	@echo ""
	@echo "mkdir-ddr-cmdln --------------------------------------------------------"
	-mkdir $(LOG_BASE)
	chown -R ddr.ddr $(LOG_BASE)
	chmod -R 775 $(LOG_BASE)
	-mkdir -p $(MEDIA_ROOT)
	chown -R ddr.ddr $(MEDIA_ROOT)
	chmod -R 775 $(MEDIA_ROOT)

test-ddr-cmdln:
	@echo ""
	@echo "test-ddr-cmdln ---------------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_CMDLN)/; pytest --disable-warnings ddr/tests/

coverage-ddr-cmdln:
	@echo ""
	@echo "coverage-ddr-cmdln -----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_CMDLN)/; pytest --cov-config=ddr-cmdln/.coveragerc --cov-report=html --cov=DDR ddr-cmdln/ddr/tests/

uninstall-ddr-cmdln: install-setuptools
	@echo ""
	@echo "uninstall-ddr-cmdln ----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_CMDLN)/ddr && pip3 uninstall -y -r requirements.txt

clean-ddr-cmdln:
	-rm -Rf $(INSTALL_CMDLN)/ddr/build
	-rm -Rf $(INSTALL_CMDLN)/ddr/ddr_cmdln.egg-info
	-rm -Rf $(INSTALL_CMDLN)/ddr/dist


get-ddr-local:
	@echo ""
	@echo "get-ddr-local ----------------------------------------------------------"
	git status | grep "On branch"
	git pull

pip-download-local:
	source $(VIRTUALENV)/bin/activate; \
	pip download --no-binary=:all: --destination-directory=$(INSTALL_LOCAL)/vendor -r $(INSTALL_LOCAL)/requirements.txt

install-ddr-local: install-setuptools mkdir-ddr-local
	@echo ""
	@echo "install-ddr-local ------------------------------------------------------"
	git status | grep "On branch"
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U --cache-dir=$(PIP_CACHE_DIR) -r $(INSTALL_LOCAL)/requirements.txt

mkdir-ddr-local:
	@echo ""
	@echo "mkdir-ddr-local --------------------------------------------------------"
# logs dir
	-mkdir $(LOG_BASE)
	chown -R ddr.ddr $(LOG_BASE)
	chmod -R 775 $(LOG_BASE)
# sqlite db dir
	-mkdir $(SQLITE_BASE)
	chown -R ddr.ddr $(SQLITE_BASE)
	chmod -R 775 $(SQLITE_BASE)
# media dir
	-mkdir -p $(MEDIA_ROOT)
	chown -R ddr.ddr $(MEDIA_ROOT)
	chmod -R 775 $(MEDIA_ROOT)
# static dir
	-mkdir -p $(STATIC_ROOT)
	chown -R ddr.ddr $(STATIC_ROOT)
	chmod -R 775 $(STATIC_ROOT)

test-ddr-local:
	@echo ""
	@echo "test-ddr-local ---------------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_LOCAL); pytest --disable-warnings ddrlocal/

shell:
	source $(VIRTUALENV)/bin/activate; \
	python ddrlocal/manage.py shell

runserver:
	source $(VIRTUALENV)/bin/activate; \
	python ddrlocal/manage.py runserver 0.0.0.0:8000

runworker:
	source $(VIRTUALENV)/bin/activate; cd $(INSTALL_LOCAL)/ddrlocal; \
	celery -A ddrlocal worker -l INFO -f /var/log/ddr/worker.log

uninstall-ddr-local: install-setuptools
	@echo ""
	@echo "uninstall-ddr-local ----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	pip3 uninstall -y -r requirements.txt

clean-ddr-local:
	-rm -Rf $(VIRTUALENV)
	-rm -Rf *.deb


get-ddr-defs:
	@echo ""
	@echo "get-ddr-defs -----------------------------------------------------------"
	git status | grep "On branch"
	if test -d $(INSTALL_DEFS); \
	then cd $(INSTALL_DEFS) && git pull; \
	else git clone $(SRC_REPO_DEFS) $(INSTALL_DEFS); \
	fi


get-densho-vocab:
	@echo ""
	@echo "get-densho-vocab -------------------------------------------------------"
	if test -d $(INSTALL_VOCAB); \
	then cd $(INSTALL_VOCAB) && git pull; \
	else git clone $(SRC_REPO_VOCAB) $(INSTALL_VOCAB); \
	fi


migrate:
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_LOCAL)/ddrlocal && $(INSTALL_LOCAL)/ddrlocal/manage.py migrate --noinput
	chown -R ddr.ddr $(SQLITE_BASE)
	chmod -R 770 $(SQLITE_BASE)
	chown -R ddr.ddr $(LOG_BASE)
	chmod -R 775 $(LOG_BASE)

branch:
	cd $(INSTALL_LOCAL)/ddrlocal; python $(INSTALL_LOCAL)/bin/git-checkout-branch.py $(BRANCH)


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
	cd $(INSTALL_STATIC)/ && tar xzf $(TAGMANAGER).tgz
	-rm $(INSTALL_STATIC)/$(TAGMANAGER).tgz

get-typeahead:
	@echo ""
	@echo "typeahead --------------------------------------------------------------"
	mkdir -p $(INSTALL_STATIC)/
	wget -nc -P $(INSTALL_STATIC)/ http://$(PACKAGE_SERVER)/$(TYPEAHEAD).tgz
	cd $(INSTALL_STATIC)/ && tar xzf $(TYPEAHEAD).tgz
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
	chown ddr.ddr $(CONF_LOCAL)
	chmod 640 $(CONF_LOCAL)

uninstall-configs:
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


get-ddr-manual:
	@echo ""
	@echo "get-ddr-manual ---------------------------------------------------------"
	git status | grep "On branch"
	if test -d $(INSTALL_MANUAL); \
	then cd $(INSTALL_MANUAL) && git pull; \
	else git clone $(SRC_REPO_MANUAL); \
	fi

install-ddr-manual: install-setuptools
	@echo ""
	@echo "install-ddr-manual -----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U --cache-dir=$(PIP_CACHE_DIR) sphinx
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_MANUAL) && make html
	rm -Rf $(MEDIA_ROOT)/manual
	mv $(INSTALL_MANUAL)/build/html $(MEDIA_ROOT)/manual

uninstall-ddr-manual:
	pip3 uninstall -y sphinx

clean-ddr-manual:
	-rm -Rf $(INSTALL_MANUAL)/build


tgz:
	rm -Rf $(TGZ_DIR)
	git clone $(INSTALL_LOCAL) $(TGZ_DIR)
	git clone $(INSTALL_CMDLN) $(TGZ_CMDLN)
	git clone $(INSTALL_CMDLN_ASSETS) $(TGZ_CMDLN_ASSETS)
	git clone $(INSTALL_DEFS) $(TGZ_DEFS)
	git clone $(INSTALL_VOCAB) $(TGZ_VOCAB)
	git clone $(INSTALL_MANUAL) $(TGZ_MANUAL)
#	git clone $(INSTALL_STATIC) $(TGZ_STATIC)
	cd $(TGZ_DIR); git checkout develop; git checkout master
	cd $(TGZ_CMDLN); git checkout develop; git checkout master
	cd $(TGZ_CMDLN_ASSETS); git checkout develop; git checkout master
	cd $(TGZ_DEFS); git checkout develop; git checkout master
	cd $(TGZ_VOCAB); git checkout develop; git checkout master
	cd $(TGZ_MANUAL); git checkout develop; git checkout master
#	cd $(TGZ_STATIC); git checkout develop; git checkout master
	tar czf $(TGZ_FILE).tgz $(TGZ_FILE)
	rm -Rf $(TGZ_DIR)


# http://fpm.readthedocs.io/en/latest/
install-fpm:
	@echo "install-fpm ------------------------------------------------------------"
	apt-get install --assume-yes ruby ruby-dev rubygems build-essential
	gem install --no-ri --no-rdoc fpm

# https://stackoverflow.com/questions/32094205/set-a-custom-install-directory-when-making-a-deb-package-with-fpm
# https://brejoc.com/tag/fpm/
deb: deb-buster

deb-stretch:
	@echo ""
	@echo "FPM packaging (stretch) ------------------------------------------------"
	-rm -Rf $(DEB_FILE_STRETCH)
# Copy .git/ dir from master worktree
	python bin/deb-prep-post.py before
# Make package
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
	--depends "cgit"   \
	--depends "fcgiwrap"   \
	--depends "git-annex"   \
	--depends "git-core"   \
	--depends "imagemagick"   \
	--depends "libexempi3"   \
	--depends "libssl-dev"   \
	--depends "libxml2"   \
	--depends "libxml2-dev"   \
	--depends "libxslt1-dev"   \
	--depends "libz-dev"   \
	--depends "nginx-light"   \
	--depends "pmount"   \
	--depends "python3-dev"   \
	--depends "python3-pip"   \
	--depends "python3-venv"   \
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
	ddr-cmdln-assets=$(DEB_BASE)   \
	ddr-defs=$(DEB_BASE)   \
	ddrlocal=$(DEB_BASE)   \
	densho-vocab=$(DEB_BASE)   \
	.git=$(DEB_BASE)   \
	.gitignore=$(DEB_BASE)   \
	INSTALL.rst=$(DEB_BASE)   \
	LICENSE=$(DEB_BASE)   \
	Makefile=$(DEB_BASE)   \
	README.rst=$(DEB_BASE)   \
	requirements.txt=$(DEB_BASE)   \
	setup-workstation.sh=$(DEB_BASE)   \
	static=$(DEB_BASE)   \
	venv=$(DEB_BASE)   \
	VERSION=$(DEB_BASE)
# Put worktree pointer file back in place
	python bin/deb-prep-post.py after

deb-buster:
	@echo ""
	@echo "FPM packaging (buster) -------------------------------------------------"
	-rm -Rf $(DEB_FILE_BUSTER)
# Copy .git/ dir from master worktree
	python bin/deb-prep-post.py before
# Make package
	fpm   \
	--verbose   \
	--input-type dir   \
	--output-type deb   \
	--name $(DEB_NAME_BUSTER)   \
	--version $(DEB_VERSION_BUSTER)   \
	--package $(DEB_FILE_BUSTER)   \
	--url "$(GIT_SOURCE_URL)"   \
	--vendor "$(DEB_VENDOR)"   \
	--maintainer "$(DEB_MAINTAINER)"   \
	--description "$(DEB_DESCRIPTION)"   \
	--depends "cgit"   \
	--depends "fcgiwrap"   \
	--depends "git-annex"   \
	--depends "git-core"   \
	--depends "imagemagick"   \
	--depends "libexempi8"   \
	--depends "libssl-dev"   \
	--depends "libxml2"   \
	--depends "libxml2-dev"   \
	--depends "libxslt1-dev"   \
	--depends "libz-dev"   \
	--depends "nginx-light"   \
	--depends "pmount"   \
	--depends "python3-dev"   \
	--depends "python3-pip"   \
	--depends "python3-venv"   \
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
	ddrlocal=$(DEB_BASE)   \
	densho-vocab=$(DEB_BASE)   \
	.git=$(DEB_BASE)   \
	.gitignore=$(DEB_BASE)   \
	INSTALL.rst=$(DEB_BASE)   \
	LICENSE=$(DEB_BASE)   \
	Makefile=$(DEB_BASE)   \
	README.rst=$(DEB_BASE)   \
	requirements.txt=$(DEB_BASE)   \
	setup-workstation.sh=$(DEB_BASE)   \
	static=$(DEB_BASE)   \
	venv=$(DEB_BASE)   \
	VERSION=$(DEB_BASE)
# Put worktree pointer file back in place
	python bin/deb-prep-post.py after
