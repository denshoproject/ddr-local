SHELL = /bin/sh

PACKAGE_SERVER=tank.densho.org

PIP_CACHE_DIR=/usr/local/src/pip-cache

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


.PHONY: help


help:
	@echo "ddr-local Install Helper"
	@echo ""
	@echo "install - Does a complete install. Idempotent, so run as many times as you like."
	@echo "          IMPORTANT: Run 'adduser ddr' first to install ddr user and group."
	@echo "          Installation instructions: make howto-install"
	@echo ""
	@echo "update  - Updates ddr-cmd and ddr-local and re-copies config files."
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
	@echo "enable-bkgnd  - Enable background processes. (Run make reload on completion)"
	@echo "disable-bkgnd - Disablebackground processes. (Run make reload on completion)"

help-all:
	@echo "install - Do a fresh install"
	@echo "install-prep    - git-config, add-user, apt-update, install-misc-tools"
	@echo "install-daemons - install-nginx install-redis install-elasticsearch"
	@echo "install-ddr     - install-ddr-cmdln install-ddr-local"
	@echo "install-static  - "
	@echo "update  - Do an update"
	@echo "restart - Restart servers"
	@echo "status  - Server status"
	@echo "cp-configs - "
	@echo "update-ddr - "
	@echo "clean-static - "

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
	@echo "- git clone https://github.com/densho/ddr-local.git /usr/local/src/ddr-local"
	@echo "- cd /usr/local/src/ddr-local/ddrlocal"
	@echo "- make install"


install: install-prep install-daemons install-ddr install-static cp-configs

update: update-ddr

clean: clean-static


install-prep: apt-update install-core git-config install-misc-tools

apt-update:
	@echo ""
	@echo "Package update ---------------------------------------------------------"
	apt-get --assume-yes update

install-core:
	apt-get --assume-yes install bzip2 curl gdebi-core git-core logrotate p7zip-full wget

git-config:
	git config --global alias.st status
	git config --global alias.co checkout
	git config --global alias.br branch
	git config --global alias.ci commit

install-misc-tools:
	@echo ""
	@echo "Installing miscellaneous tools -----------------------------------------"
	apt-get --assume-yes install ack-grep byobu elinks htop mg multitail


install-daemons: install-nginx install-redis install-elasticsearch

install-nginx:
	@echo ""
	@echo "Nginx ------------------------------------------------------------------"
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
#cp /usr/local/src/ddr-public/debian/conf/elasticsearch.yml /etc/elasticsearch/
#chown root.root /etc/elasticsearch/elasticsearch.yml
#chmod 644 /etc/elasticsearch/elasticsearch.yml
# 	@echo "${bldgrn}search engine (re)start${txtrst}"
	/etc/init.d/elasticsearch restart


install-ddr: install-ddr-cmdln install-ddr-local install-ddr-manual

update-ddr: update-ddr-cmdln update-ddr-local update-ddr-manual cp-configs


install-ddr-cmdln:
	@echo ""
	@echo "ddr-cmdln --------------------------------------------------------------"
	apt-get --assume-yes install git-core git-annex libxml2-dev libxslt1-dev libz-dev pmount udisks python-dev python-pip
	if test -d /usr/local/src/ddr-cmdln; \
	then cd /usr/local/src/ddr-cmdln && git pull; \
	else cd /usr/local/src && git clone https://github.com/densho/ddr-cmdln.git; \
	fi
	cd /usr/local/src/ddr-cmdln/ddr && python setup.py install
	cd /usr/local/src/ddr-cmdln/ddr && pip install -U --download-cache=$(PIP_CACHE_DIR) -r /usr/local/src/ddr-cmdln/ddr/requirements/production.txt
	-mkdir /var/log/ddr
	chown -R ddr.root /var/log/ddr
	chmod -R 755 /var/log/ddr

update-ddr-cmdln:
	@echo ""
	@echo "ddr-cmdln --------------------------------------------------------------"
	cd /usr/local/src/ddr-cmdln && git fetch && git pull
	cd /usr/local/src/ddr-cmdln/ddr && python setup.py install
	cd /usr/local/src/ddr-cmdln/ddr && pip install -U --download-cache=$(PIP_CACHE_DIR) -r /usr/local/src/ddr-cmdln/ddr/requirements/production.txt


install-ddr-local:
	@echo ""
	@echo "ddr-local --------------------------------------------------------------"
	apt-get --assume-yes install imagemagick libexempi3 libssl-dev python-dev libxml2 libxml2-dev libxslt1-dev supervisor
	git pull
	pip install -U --download-cache=$(PIP_CACHE_DIR) -r /usr/local/src/ddr-local/ddrlocal/requirements/production.txt
	-mkdir /var/log/ddr

update-ddr-local:
	@echo ""
	@echo "ddr-local --------------------------------------------------------------"
	git fetch && git pull
	pip install -U --download-cache=$(PIP_CACHE_DIR) -r /usr/local/src/ddr-local/ddrlocal/requirements/production.txt


install-static: install-modernizr install-bootstrap install-jquery install-tagmanager install-typeahead

clean-static: clean-modernizr clean-bootstrap clean-jquery clean-tagmanager clean-typeahead

install-modernizr:
	@echo ""
	@echo "Modernizr --------------------------------------------------------------"
	-rm /var/www/static/js/$(MODERNIZR)*
	wget -nc -P /var/www/static/js http://$(PACKAGE_SERVER)/$(MODERNIZR)

install-bootstrap:
	@echo ""
	@echo "Bootstrap --------------------------------------------------------------"
	wget -nc -P /var/www/static http://$(PACKAGE_SERVER)/$(BOOTSTRAP)
	7z x -y -o/var/www/static /var/www/static/$(BOOTSTRAP)

clean-bootstrap:
	-rm -Rf /var/www/static/$(BOOTSTRAP)

install-jquery:
	@echo ""
	@echo "jQuery -----------------------------------------------------------------"
	wget -nc -P /var/www/static/js http://$(PACKAGE_SERVER)/$(JQUERY)
	-ln -s /var/www/static/js/$(JQUERY) /var/www/static/js/jquery.js

clean-jquery:
	-rm -Rf /var/www/static/js/$(JQUERY)
	-rm /var/www/static/js/jquery.js

install-tagmanager:
	@echo ""
	@echo "tagmanager -------------------------------------------------------------"
	wget -nc -P /var/www/static/ http://$(PACKAGE_SERVER)/$(TAGMANAGER).tgz
	cd /var/www/static/ && tar xzf /var/www/static/$(TAGMANAGER).tgz
	chown -R root.root /var/www/static/$(TAGMANAGER)
	chmod 755 /var/www/static/$(TAGMANAGER)
	-ln -s /var/www/static/$(TAGMANAGER) /var/www/static/js/tagmanager

clean-tagmanager:
	-rm -Rf /var/www/static/$(TAGMANAGER).tgz
	-rm -Rf /var/www/static/$(TAGMANAGER)
	-rm /var/www/static/js/tagmanager

install-typeahead: clean-typeahead
	@echo ""
	@echo "typeahead --------------------------------------------------------------"
	wget -nc -P /var/www/static/ http://$(PACKAGE_SERVER)/$(TYPEAHEAD).tgz
	cd /var/www/static/ && tar xzf /var/www/static/$(TYPEAHEAD).tgz
	chown -R root.root /var/www/static/$(TYPEAHEAD)
	-ln -s /var/www/static/$(TYPEAHEAD) /var/www/static/js/typeahead

clean-typeahead:
	-rm -Rf /var/www/static/$(TYPEAHEAD).tgz
	-rm -Rf /var/www/static/$(TYPEAHEAD)
	-rm /var/www/static/js/typeahead


cp-configs:
	@echo ""
	@echo "configuring ddr-local --------------------------------------------------"
# base settings file
	-mkdir /etc/ddr
	cp /usr/local/src/ddr-local/debian/conf/ddr.cfg /etc/ddr/
	chown root.root /etc/ddr/ddr.cfg
	chmod 644 /etc/ddr/ddr.cfg
# web app settings
	cp /usr/local/src/ddr-local/debian/conf/settings.py /usr/local/src/ddr-local/ddrlocal/ddrlocal/
	chown root.root /usr/local/src/ddr-local/ddrlocal/ddrlocal/settings.py
	chmod 644 /usr/local/src/ddr-local/ddrlocal/ddrlocal/settings.py
# nginx settings
	cp /usr/local/src/ddr-local/debian/conf/ddrlocal.conf /etc/nginx/sites-available
	chown root.root /etc/nginx/sites-available/ddrlocal.conf
	chmod 644 /etc/nginx/sites-available/ddrlocal.conf
	-ln -s /etc/nginx/sites-available/ddrlocal.conf /etc/nginx/sites-enabled/ddrlocal.conf
	-rm /etc/nginx/sites-enabled/default
# supervisord
	cp /usr/local/src/ddr-local/debian/conf/supervisord.conf /etc/supervisor/
	cp /usr/local/src/ddr-local/debian/conf/celeryd.conf /etc/supervisor/conf.d/
	cp /usr/local/src/ddr-local/debian/conf/gunicorn_ddrlocal.conf /etc/supervisor/conf.d/
	chown root.root /etc/supervisor/conf.d/celeryd.conf
	chown root.root /etc/supervisor/conf.d/gunicorn_ddrlocal.conf
	chmod 644 /etc/supervisor/conf.d/celeryd.conf
	chmod 644 /etc/supervisor/conf.d/gunicorn_ddrlocal.conf


enable-bkgnd:
	cp /usr/local/src/ddr-local/debian/conf/celerybeat.conf /etc/supervisor/conf.d/
	chown root.root /etc/supervisor/conf.d/celerybeat.conf
	chmod 644 /etc/supervisor/conf.d/celerybeat.conf

disable-bkgnd:
	-rm /etc/supervisor/conf.d/celerybeat.conf


reload: reload-nginx reload-supervisor

reload-nginx:
	/etc/init.d/nginx reload

reload-supervisor:
	supervisorctl reload


restart: restart-elasticsearch restart-redis restart-nginx restart-supervisor

restart-elasticsearch:
	/etc/init.d/elasticsearch restart

restart-redis:
	/etc/init.d/redis-server restart

restart-nginx:
	/etc/init.d/nginx restart

restart-supervisor:
	/etc/init.d/supervisor restart


status:
	/etc/init.d/redis-server status
	/etc/init.d/elasticsearch status
	/etc/init.d/nginx status
	supervisorctl status

git-status:
	@echo "------------------------------------------------------------------------"
	cd /usr/local/src/ddr-cmdln && git status
	@echo "------------------------------------------------------------------------"
	cd /usr/local/src/ddr-local && git status


install-ddr-manual:
	@echo ""
	@echo "ddr-manual --------------------------------------------------------------"
	if test -d /usr/local/src/ddr-manual; \
	then cd /usr/local/src/ddr-manual && git pull; \
	else cd /usr/local/src && git clone https://github.com/densho/ddr-manual.git; \
	fi
	cd /usr/local/src/ddr-manual && make html

update-ddr-manual:
	@echo ""
	@echo "ddr-manual --------------------------------------------------------------"
	cd /usr/local/src/ddr-manual && git fetch && git pull
	cd /usr/local/src/ddr-manual && make html
