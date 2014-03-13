# This script performs all the steps in the "DDR Applications and Dependencies"
# section of the "Creating a Workstation VM" page from the DDR Manual
# 

PIP_CACHE_DIR=/usr/local/src/pip-cache

BOOTSTRAP=bootstrap-2.3.1.zip
MODERNIZR=modernizr-2.6.2.js
JQUERY=jquery-1.10.2.min.js

ELASTICSEARCH=elasticsearch-0.90.5.deb


# text color variables
txtund=$(tput sgr 0 1)   # underline
txtbld=$(tput bold)      # bold
red=$(tput setaf 1)      # red
grn=$(tput setaf 2)      # green
blu=$(tput setaf 4)      # blue
wht=$(tput setaf 7)      # white
bldred=${txtbld}${red}   # red
bldgrn=${txtbld}${grn}   # green
bldblu=${txtbld}${blu}   # blue
bldwht=${txtbld}${wht}   # white
txtrst=$(tput sgr0)      # reset
info=${bldwht}*${txtrst} # feedback
pass=${bldblu}*${txtrst}
warn=${bldred}*${txtrst}
ques=${bldblu}?${txtrst}


git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit


echo "${bldgrn}Creating ddr user${txtrst}"
adduser ddr
adduser ddr vboxsf


echo "${bldgrn}Package update${txtrst}"
apt-get --assume-yes update


echo "${bldgrn}Installing miscellaneous tools${txtrst}"
apt-get --assume-yes install ack-grep byobu bzip2 curl elinks gdebi-core htop logrotate mg multitail p7zip-full wget


echo "${bldgrn}www server${txtrst}"
apt-get --assume-yes install nginx


echo "${bldgrn}cache server${txtrst}"
apt-get --assume-yes install redis-server


echo "${bldgrn}search engine${txtrst}"
apt-get --assume-yes install openjdk-6-jre
wget -nc -P /tmp/downloads http://tank.densho.org/$ELASTICSEARCH
gdebi --non-interactive /tmp/downloads/$ELASTICSEARCH

echo "${bldgrn}ddr-cmdln${txtrst}"
apt-get --assume-yes install git-core git-annex libxml2-dev libxslt1-dev pmount udisks python-dev python-pip
cd /usr/local/src
git clone https://github.com/densho/ddr-cmdln.git
cd /usr/local/src/ddr-cmdln/ddr
python setup.py install
pip install --download-cache=$PIP_CACHE_DIR -r /usr/local/src/ddr-cmdln/ddr/requirements/production.txt
adduser ddr plugdev


echo "${bldgrn}ddr-lint${txtrst}"
apt-get --assume-yes install libxml2 libxml2-dev libxslt1-dev
cd /usr/local/src
git clone https://github.com/densho/ddr-lint.git
cd /usr/local/src/ddr-lint/ddrlint
python setup.py install
pip install --download-cache=$PIP_CACHE_DIR -r /usr/local/src/ddr-cmdln/ddr/requirements/production.txt


echo "${bldgrn}ddr-local${txtrst}"
apt-get --assume-yes install imagemagick libexempi3 libssl-dev python-dev libxml2 libxml2-dev libxslt1-dev supervisor
cd /usr/local/src
git clone https://github.com/densho/ddr-local.git
cd /usr/local/src/ddr-local/ddrlocal
pip install --download-cache=$PIP_CACHE_DIR -r /usr/local/src/ddr-local/ddrlocal/requirements/production.txt


echo "${bldgrn}creating directories${txtrst}"
mkdir /etc/ddr
mkdir /etc/ddr/templates
mkdir /var/log/ddr
mkdir /var/lib/ddr
mkdir /var/www
mkdir /var/www/media
mkdir /var/www/media/cache
mkdir /var/www/static
mkdir /var/www/static/js
chown -R ddr /var/log/ddr/
chown -R ddr /var/lib/ddr/
chown -R ddr /var/www/media


echo "${bldgrn}Bootstrap, jQuery, Modernizr${txtrst}"
rm /var/www/static/$BOOTSTRAP*
rm /var/www/static/js/$MODERNIZR*
rm /var/www/static/js/$JQUERY*
wget -nc -P /var/www/static http://tank.densho.org/$BOOTSTRAP
7z x -y -o/var/www/static /var/www/static/$BOOTSTRAP
wget -nc -P /var/www/static/js http://tank.densho.org/$MODERNIZR
wget -nc -P /var/www/static/js http://tank.densho.org/$JQUERY
ln -s /var/www/static/js/$JQUERY /var/www/static/js/jquery.js


echo "${bldgrn}configuration files${txtrst}"
cp /usr/local/src/ddr-local/debian/conf/ddr.cfg /etc/ddr/
chown root.root /etc/ddr/ddr.cfg
chmod 644 /etc/ddr/ddr.cfg

cp /usr/local/src/ddr-local/debian/conf/templates/* /etc/ddr/templates/
chown root.root /etc/ddr/templates/*
chmod 644 /etc/ddr/templates/*

cp /usr/local/src/ddr-local/debian/conf/settings.py /usr/local/src/ddr-local/ddrlocal/ddrlocal/
chown root.root /usr/local/src/ddr-local/ddrlocal/ddrlocal/settings.py
chmod 644 /usr/local/src/ddr-local/ddrlocal/ddrlocal/settings.py

cp /usr/local/src/ddr-local/debian/conf/supervisord.conf /etc/supervisor/
cp /usr/local/src/ddr-local/debian/conf/celeryd.conf /etc/supervisor/conf.d/
cp /usr/local/src/ddr-local/debian/conf/gunicorn_ddrlocal.conf /etc/supervisor/conf.d/
chown root.root /etc/supervisor/conf.d/celeryd.conf
chown root.root /etc/supervisor/conf.d/gunicorn_ddrlocal.conf
chmod 644 /etc/supervisor/conf.d/celeryd.conf
chmod 644 /etc/supervisor/conf.d/gunicorn_ddrlocal.conf
/etc/init.d/supervisor restart

cp /usr/local/src/ddr-local/debian/conf/ddrlocal.conf /etc/nginx/sites-available
ln -s /etc/nginx/sites-available/ddrlocal.conf /etc/nginx/sites-enabled
/etc/init.d/nginx restart

/etc/init.d/elasticsearch restart
