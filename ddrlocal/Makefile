SHELL = /bin/bash
DEBIAN_CODENAME := $(shell lsb_release -sc)

PACKAGE_SERVER=ddr.densho.org/static/ddrlocal

INSTALL_BASE=/usr/local/src
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache
VIRTUALENV=$(INSTALL_BASE)/env/ddrlocal
INSTALLDIR=$(INSTALL_BASE)/ddr-local
SETTINGS=$(INSTALLDIR)/ddrlocal/ddrlocal/settings.py

CONF_BASE=/etc/ddr
CONF_PRODUCTION=$(CONF_BASE)/ddrlocal.cfg
CONF_LOCAL=$(CONF_BASE)/ddrlocal-local.cfg
CONF_SECRET=$(CONF_BASE)/ddrlocal-secret-key.txt

SQLITE_BASE=/var/lib/ddr
LOG_BASE=/var/log/ddr

DDR_REPO_BASE=/var/www/media

MEDIA_BASE=/var/www/ddrlocal
MEDIA_ROOT=$(MEDIA_BASE)/media
STATIC_ROOT=$(MEDIA_BASE)/static

ELASTICSEARCH=elasticsearch-1.0.1.deb
MODERNIZR=modernizr-2.6.2.js
JQUERY=jquery-1.11.0.min.js
BOOTSTRAP=bootstrap-3.1.1-dist.zip
TAGMANAGER=tagmanager-3.0.1
TYPEAHEAD=typeahead-0.10.2
# wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.0.1.deb
# wget http://code.jquery.com/jquery-1.11.0.min.js
# wget https://github.com/twbs/bootstrap/releases/download/v3.1.1/bootstrap-3.1.1-dist.zip
# wget https://github.com/max-favilli/tagmanager/archive/v3.0.1.tar.gz
# wget https://github.com/twitter/typeahead.js/archive/v0.10.2.tar.gz

SUPERVISOR_CELERY_CONF=/etc/supervisor/conf.d/celeryd.conf
SUPERVISOR_CELERYBEAT_CONF=/etc/supervisor/conf.d/celerybeat.conf
SUPERVISOR_GUNICORN_CONF=/etc/supervisor/conf.d/gunicorn_ddrlocal.conf
SUPERVISOR_CONF=/etc/supervisor/supervisord.conf
NGINX_CONF=/etc/nginx/sites-available/ddrlocal.conf
NGINX_CONF_LINK=/etc/nginx/sites-enabled/ddrlocal.conf
MUNIN_CONF=/etc/munin/munin.conf
GITWEB_CONF=/etc/gitweb.conf
CGIT_CONF=/etc/cgitrc


.PHONY: help


help:
	@echo "ddr-local Install Helper"
	@echo ""
	@echo "install - Does a complete install. Idempotent, so run as many times as you like."
	@echo "          IMPORTANT: Run 'adduser ddr' first to install ddr user and group."
	@echo "          Installation instructions: make howto-install"
	@echo ""
	@echo "enable-bkgnd  - Enable background processes. (Run make reload on completion)"
	@echo "disable-bkgnd - Disablebackground processes. (Run make reload on completion)"
	@echo ""
	@echo "syncdb  - Initialize or update Django app's database tables."
	@echo ""
	@echo "branch BRANCH=[branch] - Switches both ddr-local and ddr-cmdln repos to [branch]."
	@echo ""
	@echo "reload  - Reloads supervisord and nginx configs"
	@echo "reload-nginx"
	@echo "reload-supervisors"
	@echo ""
	@echo "restart - Restarts all servers"
	@echo "restart-elasticsearch"
	@echo "restart-redis"
	@echo "restart-nginx"
	@echo "restart-supervisord"
	@echo ""
	@echo "status  - Server status"
	@echo ""
	@echo "uninstall - Deletes 'compiled' Python files. Leaves build dirs and configs."
	@echo "clean   - Deletes files created by building the program. Leaves configs."

help-all:
	@echo "install - Do a fresh install"
	@echo "install-prep    - git-config, add-user, apt-update, install-misc-tools"
	@echo "install-daemons - install-nginx install-redis install-elasticsearch"
	@echo "install-app     - install-ddr-cmdln install-ddr-local"
	@echo "install-static  - "
	@echo "restart - Restart servers"
	@echo "status  - Server status"
	@echo "install-configs - "
	@echo "update-ddr - "
	@echo "uninstall - "
	@echo "clean - "

howto-install:
	@echo "HOWTO INSTALL"
	@echo "- Basic Debian netinstall"
	@echo "- edit /etc/network/interfaces"
	@echo "- reboot"
	@echo "- apt-get install openssh fail2ban ufw"
	@echo "- ufw allow 22/tcp"
	@echo "- ufw allow 80/tcp"
	@echo "- ufw enable"
	@echo "- apt-get install make"
	@echo "- adduser ddr"
	@echo "- git clone https://github.com/densho/ddr-local.git $(INSTALLDIR)"
	@echo "- cd $(INSTALLDIR)/ddrlocal"
	@echo "- make install"
	@echo "- [make branch BRANCH=develop]"
	@echo "- [make install]"
	@echo "- make enable-bkgnd"
	@echo "- Place copy of 'ddr' repo in /var/www/media/ddr/ddr."
	@echo "- make syncdb"
	@echo "- make restart"
	@echo "- [make clear-munin-logs]"


get: get-ddr-cmdln get-ddr-local

install: install-prep get-app install-daemons install-app install-static install-configs

uninstall: uninstall-app uninstall-configs

clean: clean-app


install-prep: ddr-user apt-backports apt-update install-core git-config install-misc-tools

ddr-user:
	-addgroup ddr plugdev
	-addgroup ddr vboxsf
	if ! grep "bin/activate" /home/ddr/.bashrc ; \
	then printf "\n\n# ddrlocal: Activate virtualnv on login\nsource /usr/local/src/env/ddrlocal/bin/activate\n" >> /home/ddr/.bashrc; \
	fi

apt-backports:
ifeq "$(DEBIAN_CODENAME)" "wheezy"
	cp $(INSTALLDIR)/debian/conf/wheezy-backports.list /etc/apt/sources.list.d/
endif

apt-update:
	@echo ""
	@echo "Package update ---------------------------------------------------------"
	apt-get --assume-yes update

apt-upgrade:
	@echo ""
	@echo "Package upgrade --------------------------------------------------------"
	apt-get --assume-yes upgrade

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


install-daemons: install-elasticsearch install-redis install-cgit install-munin install-nginx

install-cgit:
	@echo ""
	@echo "gitweb/cgit ------------------------------------------------------------"
#ifeq ($(DEBIAN_CODENAME), wheezy)
# 	apt-get --assume-yes -t wheezy-backports install cgit
#endif
ifeq ($(DEBIAN_CODENAME), jessie)
	apt-get --assume-yes install cgit fcgiwrap
endif
	-mkdir /var/www/cgit
	-ln -s /usr/lib/cgit/cgit.cgi /var/www/cgit/cgit.cgi
	-ln -s /usr/share/cgit/cgit.css /var/www/cgit/cgit.css
	-ln -s /usr/share/cgit/favicon.ico /var/www/cgit/favicon.ico
	-ln -s /usr/share/cgit/robots.txt /var/www/cgit/robots.txt

install-munin:
	@echo ""
	@echo "Munin ------------------------------------------------------------------"
	apt-get --assume-yes install munin munin-node libwww-perl
	if test -d $(INSTALL_BASE)/munin-monitoring; \
	then cd $(INSTALL_BASE)/munin-monitoring && git pull; \
	else cd $(INSTALL_BASE) && git clone https://github.com/munin-monitoring/contrib.git $(INSTALL_BASE)/munin-monitoring; \
	fi
	-rm /etc/munin/plugins/exim_*
	-rm /etc/munin/plugins/entropy
	-rm /etc/munin/plugins/fail2ban
	-rm /etc/munin/plugins/if_err_*
	-rm /etc/munin/plugins/munin_stats
	-rm /etc/munin/plugins/nfsd
	-rm /etc/munin/plugins/nfsd4
	-rm /etc/munin/plugins/ntp_*
	cd /etc/munin/plugins/
	-ln -s /usr/share/munin/plugins/nginx_request /etc/munin/plugins/nginx_request
	-ln -s /usr/share/munin/plugins/nginx_status /etc/munin/plugins/nginx_status
	-ln -s $(INSTALL_BASE)/munin-monitoring/plugins/redis/redis_ /etc/munin/plugins/redis_
#- celery
#- Elasticsearch
#- ping gitolite

clear-munin-logs:
# NOTE: This erases Munin history!
	rm -Rf /var/cache/munin/www/*


install-nginx:
	@echo ""
	@echo "Nginx ------------------------------------------------------------------"
	apt-get --assume-yes remove apache2
	apt-get --assume-yes install nginx

install-redis:
	@echo ""
	@echo "Redis ------------------------------------------------------------------"
	apt-get --assume-yes install redis-server

install-elasticsearch:
	@echo ""
	@echo "Elasticsearch ----------------------------------------------------------"
# Elasticsearch is configured/restarted here so it's online by the time script is done.
	apt-get --assume-yes install openjdk-7-jre
	wget -nc -P /tmp/downloads http://$(PACKAGE_SERVER)/$(ELASTICSEARCH)
	gdebi --non-interactive /tmp/downloads/$(ELASTICSEARCH)
#cp $(INSTALL_BASE)/ddr-public/debian/conf/elasticsearch.yml /etc/elasticsearch/
#chown root.root /etc/elasticsearch/elasticsearch.yml
#chmod 644 /etc/elasticsearch/elasticsearch.yml
# 	@echo "${bldgrn}search engine (re)start${txtrst}"
	/etc/init.d/elasticsearch restart


install-virtualenv:
	@echo ""
	@echo "install-virtualenv -----------------------------------------------------"
	apt-get --assume-yes install python-pip python-virtualenv
	test -d $(VIRTUALENV) || virtualenv --distribute --setuptools $(VIRTUALENV)

install-setuptools: install-virtualenv
	@echo ""
	@echo "install-setuptools -----------------------------------------------------"
	apt-get --assume-yes install python-dev
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --download-cache=$(PIP_CACHE_DIR) bpython setuptools


get-app: get-ddr-cmdln get-ddr-local get-ddr-manual

install-app: install-git-annex install-virtualenv install-setuptools install-ddr-cmdln install-ddr-local install-ddr-manual install-configs install-daemon-configs

uninstall-app: uninstall-ddr-cmdln uninstall-ddr-local uninstall-ddr-manual uninstall-configs uninstall-daemon-configs

clean-app: clean-ddr-cmdln clean-ddr-local clean-ddr-manual


install-git-annex:
ifeq "$(DEBIAN_CODENAME)" "wheezy"
	apt-get --assume-yes -t wheezy-backports install git-core git-annex
endif
ifeq "($(DEBIAN_CODENAME)" "jessie"
	apt-get --assume-yes install git-core git-annex
endif

get-ddr-cmdln:
	@echo ""
	@echo "get-ddr-cmdln ----------------------------------------------------------"
	if test -d $(INSTALL_BASE)/ddr-cmdln; \
	then cd $(INSTALL_BASE)/ddr-cmdln && git pull; \
	else cd $(INSTALL_BASE) && git clone https://github.com/densho/ddr-cmdln.git; \
	fi

install-ddr-cmdln:
	@echo ""
	@echo "install-ddr-cmdln ------------------------------------------------------"
	apt-get --assume-yes install git-core git-annex libxml2-dev libxslt1-dev libz-dev pmount udisks
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_BASE)/ddr-cmdln/ddr && python setup.py install
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_BASE)/ddr-cmdln/ddr && pip install -U --download-cache=$(PIP_CACHE_DIR) -r $(INSTALL_BASE)/ddr-cmdln/ddr/requirements/production.txt
	-mkdir $(LOG_BASE)
	chown -R ddr.root $(LOG_BASE)
	chmod -R 755 $(LOG_BASE)
	-mkdir -p $(MEDIA_ROOT)
	chown -R ddr.root $(MEDIA_ROOT)
	chmod -R 755 $(MEDIA_ROOT)

uninstall-ddr-cmdln:
	@echo ""
	@echo "uninstall-ddr-cmdln ----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALL_BASE)/ddr-cmdln/ddr && pip uninstall -y -r $(INSTALL_BASE)/ddr-cmdln/ddr/requirements/production.txt
	-rm /usr/local/bin/ddr*
	-rm -Rf /usr/local/lib/python2.7/dist-packages/DDR*
	-rm -Rf /usr/local/lib/python2.7/dist-packages/ddr*

clean-ddr-cmdln:
	-rm -Rf $(INSTALL_BASE)/ddr-cmdln/ddr/build


get-ddr-local:
	@echo ""
	@echo "get-ddr-local ----------------------------------------------------------"
	git pull

install-ddr-local:
	@echo ""
	@echo "install-ddr-local ------------------------------------------------------"
	apt-get --assume-yes install imagemagick libexempi3 libssl-dev python-dev libxml2 libxml2-dev libxslt1-dev supervisor
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --download-cache=$(PIP_CACHE_DIR) -r $(INSTALLDIR)/ddrlocal/requirements/production.txt
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

uninstall-ddr-local:
	@echo ""
	@echo "uninstall-ddr-local ----------------------------------------------------"
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALLDIR)/ddrlocal && pip uninstall -y -r $(INSTALLDIR)/ddrlocal/requirements/production.txt
	-rm /usr/local/lib/python2.7/dist-packages/ddrlocal-*
	-rm -Rf /usr/local/lib/python2.7/dist-packages/ddrlocal

clean-ddr-local:
	-rm -Rf $(INSTALLDIR)/ddrlocal/src

clean-pip:
	-rm -Rf $(PIP_CACHE_DIR)/*


syncdb:
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALLDIR)/ddrlocal && ./manage.py syncdb --noinput
	chown -R ddr.root $(SQLITE_BASE)
	chmod -R 750 $(SQLITE_BASE)
	chown -R ddr.root $(LOG_BASE)
	chmod -R 755 $(LOG_BASE)

branch:
	cd $(INSTALLDIR)/ddrlocal; python ./bin/git-checkout-branch.py $(BRANCH)


install-static: install-modernizr install-bootstrap install-jquery install-tagmanager install-typeahead

clean-static: clean-modernizr clean-bootstrap clean-jquery clean-tagmanager clean-typeahead


install-modernizr:
	@echo ""
	@echo "Modernizr --------------------------------------------------------------"
	-rm $(STATIC_ROOT)/js/$(MODERNIZR)*
	wget -nc -P $(STATIC_ROOT)/js http://$(PACKAGE_SERVER)/$(MODERNIZR)

clean-modernizr:
	-rm $(STATIC_ROOT)/js/$(MODERNIZR)*

install-bootstrap:
	@echo ""
	@echo "Bootstrap --------------------------------------------------------------"
	wget -nc -P $(STATIC_ROOT) http://$(PACKAGE_SERVER)/$(BOOTSTRAP)
	7z x -y -o$(STATIC_ROOT) $(STATIC_ROOT)/$(BOOTSTRAP)

clean-bootstrap:
	-rm -Rf $(STATIC_ROOT)/$(BOOTSTRAP)

install-jquery:
	@echo ""
	@echo "jQuery -----------------------------------------------------------------"
	wget -nc -P $(STATIC_ROOT)/js http://$(PACKAGE_SERVER)/$(JQUERY)
	-ln -s $(STATIC_ROOT)/js/$(JQUERY) $(STATIC_ROOT)/js/jquery.js

clean-jquery:
	-rm -Rf $(STATIC_ROOT)/js/$(JQUERY)
	-rm $(STATIC_ROOT)/js/jquery.js

install-tagmanager:
	@echo ""
	@echo "tagmanager -------------------------------------------------------------"
	wget -nc -P $(STATIC_ROOT)/ http://$(PACKAGE_SERVER)/$(TAGMANAGER).tgz
	cd $(STATIC_ROOT)/ && tar xzf $(STATIC_ROOT)/$(TAGMANAGER).tgz
	chown -R root.root $(STATIC_ROOT)/$(TAGMANAGER)
	chmod 755 $(STATIC_ROOT)/$(TAGMANAGER)
	-ln -s $(STATIC_ROOT)/$(TAGMANAGER) $(STATIC_ROOT)/js/tagmanager

clean-tagmanager:
	-rm -Rf $(STATIC_ROOT)/$(TAGMANAGER).tgz
	-rm -Rf $(STATIC_ROOT)/$(TAGMANAGER)
	-rm $(STATIC_ROOT)/js/tagmanager

install-typeahead: clean-typeahead
	@echo ""
	@echo "typeahead --------------------------------------------------------------"
	wget -nc -P $(STATIC_ROOT)/ http://$(PACKAGE_SERVER)/$(TYPEAHEAD).tgz
	cd $(STATIC_ROOT)/ && tar xzf $(STATIC_ROOT)/$(TYPEAHEAD).tgz
	chown -R root.root $(STATIC_ROOT)/$(TYPEAHEAD)
	-ln -s $(STATIC_ROOT)/$(TYPEAHEAD) $(STATIC_ROOT)/js/typeahead

clean-typeahead:
	-rm -Rf $(STATIC_ROOT)/$(TYPEAHEAD).tgz
	-rm -Rf $(STATIC_ROOT)/$(TYPEAHEAD)
	-rm $(STATIC_ROOT)/js/typeahead


install-configs:
	@echo ""
	@echo "configuring ddr-local --------------------------------------------------"
# base settings file
	-mkdir /etc/ddr
	cp $(INSTALLDIR)/debian/conf/ddr.cfg $(CONF_PRODUCTION)
	chown root.root $(CONF_PRODUCTION)
	chmod 644 $(CONF_PRODUCTION)
# web app settings
	cp $(INSTALLDIR)/debian/conf/settings.py $(SETTINGS)
	chown root.root $(SETTINGS)
	chmod 644 $(SETTINGS)

uninstall-configs:
	-rm $(SETTINGS)
	-rm $(CONF_PRODUCTION)


install-daemon-configs:
	@echo ""
	@echo "install-daemon-configs -------------------------------------------------"
# nginx settings
	cp $(INSTALLDIR)/debian/conf/ddrlocal.conf $(NGINX_CONF)
	chown root.root $(NGINX_CONF)
	chmod 644 $(NGINX_CONF)
	-ln -s $(NGINX_CONF) $(NGINX_CONF_LINK)
	-rm /etc/nginx/sites-enabled/default
# supervisord
	cp $(INSTALLDIR)/debian/conf/celeryd.conf $(SUPERVISOR_CELERY_CONF)
	cp $(INSTALLDIR)/debian/conf/gunicorn_ddrlocal.conf $(SUPERVISOR_GUNICORN_CONF)
	cp $(INSTALLDIR)/debian/conf/supervisord.conf $(SUPERVISOR_CONF)
	chown root.root $(SUPERVISOR_CELERY_CONF)
	chown root.root $(SUPERVISOR_GUNICORN_CONF)
	chown root.root $(SUPERVISOR_CONF)
	chmod 644 $(SUPERVISOR_CELERY_CONF)
	chmod 644 $(SUPERVISOR_GUNICORN_CONF)
	chmod 644 $(SUPERVISOR_CONF)
# gitweb
	cp $(INSTALLDIR)/debian/conf/gitweb.conf $(GITWEB_CONF)
	cp $(INSTALLDIR)/debian/conf/cgitrc $(CGIT_CONF)
# munin settings
	cp $(INSTALLDIR)/debian/conf/munin.conf $(MUNIN_CONF)
	chown root.root $(MUNIN_CONF)
	chmod 644 $(MUNIN_CONF)

uninstall-daemon-configs:
	-rm $(NGINX_CONF)
	-rm $(NGINX_CONF_LINK)
	-rm $(MUNIN_CONF)
	-rm $(SUPERVISOR_CELERY_CONF)
	-rm $(SUPERVISOR_CONF)
	-rm $(GITWEB_CONF)


enable-bkgnd:
	cp $(INSTALLDIR)/debian/conf/celerybeat.conf $(SUPERVISOR_CELERYBEAT_CONF)
	chown root.root $(SUPERVISOR_CELERYBEAT_CONF)
	chmod 644 $(SUPERVISOR_CELERYBEAT_CONF)

disable-bkgnd:
	-rm $(SUPERVISOR_CELERYBEAT_CONF)


reload: reload-nginx reload-supervisor

reload-nginx:
	/etc/init.d/nginx reload

reload-supervisor:
	supervisorctl reload

reload-app: reload-supervisor


stop: stop-elasticsearch stop-redis stop-nginx stop-munin stop-supervisor

stop-elasticsearch:
	/etc/init.d/elasticsearch stop

stop-redis:
	/etc/init.d/redis-server stop

stop-nginx:
	/etc/init.d/nginx stop

stop-munin:
	/etc/init.d/munin-node stop
	/etc/init.d/munin stop

stop-supervisor:
	/etc/init.d/supervisor stop

stop-app: stop-supervisor


restart: restart-elasticsearch restart-redis restart-cgit restart-nginx restart-munin restart-supervisor

restart-elasticsearch:
	/etc/init.d/elasticsearch restart

restart-redis:
	/etc/init.d/redis-server restart

restart-cgit:
	/etc/init.d/fcgiwrap restart

restart-nginx:
	/etc/init.d/nginx restart

restart-munin:
	/etc/init.d/munin-node restart
	/etc/init.d/munin restart

restart-supervisor:
	/etc/init.d/supervisor stop
	/etc/init.d/supervisor start

restart-app: restart-supervisor


status:
	@echo "------------------------------------------------------------------------"
	-/etc/init.d/elasticsearch status
	@echo " - - - - -"
	-/etc/init.d/redis-server status
	@echo " - - - - -"
	-/etc/init.d/nginx status
	@echo " - - - - -"
	-supervisorctl status
	@echo " - - - - -"
	-git annex version | grep version
	@echo ""

git-status:
	@echo "------------------------------------------------------------------------"
	cd $(INSTALL_BASE)/ddr-cmdln && git status
	@echo "------------------------------------------------------------------------"
	cd $(INSTALLDIR) && git status


get-ddr-manual:
	@echo ""
	@echo "get-ddr-manual ---------------------------------------------------------"
	if test -d $(INSTALL_BASE)/ddr-manual; \
	then cd $(INSTALL_BASE)/ddr-manual && git pull; \
	else cd $(INSTALL_BASE) && git clone https://github.com/densho/ddr-manual.git; \
	fi

install-ddr-manual:
	@echo ""
	@echo "install-ddr-manual -----------------------------------------------------"
	pip install -U --download-cache=$(PIP_CACHE_DIR) sphinx
	cd $(INSTALL_BASE)/ddr-manual && make html
	mv $(INSTALL_BASE)/ddr-manual/build/html $(MEDIA_ROOT)/manual

uninstall-ddr-manual:
	pip uninstall -y sphinx

clean-ddr-manual:
	-rm -Rf $(INSTALL_BASE)/ddr-manual/build
