# This script performs all the steps in the "DDR Applications and Dependencies"
# section of the "Creating a Workstation VM" page from the DDR Manual
# 


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
apt-get --assume-yes install ack-grep byobu bzip2 curl elinks htop logrotate mg multitail p7zip-full wget


echo "${bldgrn}www server${txtrst}"
apt-get --assume-yes install nginx


echo "${bldgrn}cache server${txtrst}"
apt-get --assume-yes install redis-server


echo "${bldgrn}ddr-cmdln${txtrst}"
apt-get --assume-yes install git-core git-annex libxml2-dev libxslt1-dev pmount udisks python-dev python-pip
cd /usr/local/src
git clone https://github.com/densho/ddr-cmdln.git
cd /usr/local/src/ddr-cmdln/ddr
python setup.py install
pip install -r /usr/local/src/ddr-cmdln/ddr/requirements/production.txt
adduser ddr plugdev


echo "${bldgrn}ddr-lint${txtrst}"
apt-get --assume-yes install libxml2 libxml2-dev libxslt1-dev
cd /usr/local/src
git clone https://github.com/densho/ddr-lint.git
cd /usr/local/src/ddr-lint/ddrlint
python setup.py install
pip install -r /usr/local/src/ddr-cmdln/ddr/requirements/production.txt


echo "${bldgrn}ddr-local${txtrst}"
apt-get --assume-yes install imagemagick libssl-dev python-dev libxml2 libxml2-dev libxslt1-dev supervisor
cd /usr/local/src
git clone https://github.com/densho/ddr-local.git
cd /usr/local/src/ddr-local/ddrlocal
pip install -r /usr/local/src/ddr-local/ddrlocal/requirements/production.txt


echo "${bldgrn}creating directories${txtrst}"
mkdir /etc/ddr
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
cd /var/www/static
wget http://twitter.github.io/bootstrap/assets/bootstrap.zip
7z x bootstrap.zip
cd /var/www/static/js
wget http://modernizr.com/downloads/modernizr-latest.js
wget http://code.jquery.com/jquery-1.10.2.min.js
ln -s jquery-1.10.2.min.js jquery.js


echo "${bldgrn}configuration files${txtrst}"
cp /usr/local/src/ddr-local/debian/conf/ddr.cfg /etc/ddr/
chown root.root /etc/ddr/ddr.cfg
chmod 644 /etc/ddr/ddr.cfg

cp /usr/local/src/ddr-local/debian/conf/settings.py /usr/local/src/ddr-local/ddrlocal/ddrlocal/
chown root.root /usr/local/src/ddr-local/ddrlocal/ddrlocal/settings.py
chmod 644 /usr/local/src/ddr-local/ddrlocal/ddrlocal/settings.py

cp /usr/local/src/ddr-local/debian/conf/celeryd.conf /etc/supervisor/conf.d/
cp /usr/local/src/ddr-local/debian/conf/gunicorn_ddrlocal.conf /etc/supervisor/conf.d/
chown root.root /etc/supervisor/conf.d/celeryd.conf
chown root.root /etc/supervisor/conf.d/gunicorn_ddrlocal.conf
chmod 644 /etc/supervisor/conf.d/celeryd.conf
chmod 644 /etc/supervisor/conf.d/gunicorn_ddrlocal.conf

supervisorctl reload
supervisorctl restart celery
supervisorctl restart ddrlocal

cp /usr/local/src/ddr-local/debian/conf/ddrlocal.conf /etc/nginx/sites-available
ln -s /etc/nginx/sites-available/ddrlocal.conf /etc/nginx/sites-enabled
/etc/init.d/nginx restart


