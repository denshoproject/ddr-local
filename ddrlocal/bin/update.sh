# update.sh - Pulls down new code, copies configs, restarts
#
# NOTE: This script must be run as root!
# 
# WARNING: This script makes assumptions!
# - That ddr-local is installed in /usr/local/src.
# - That ddr-cmdln is installed in /usr/local/src.
# If these is not the case, expect breakage!
#
# NOTE: Does not flush caches.


echo "ddr-lint"
cd /usr/local/src/ddr-lint

echo "git fetch"
git fetch

echo "git pull"
git pull

echo "python setup.py install"
cd /usr/local/src/ddr-lint/ddrlint
python setup.py install


echo "ddr-cmdln"
cd /usr/local/src/ddr-cmdln

echo "git fetch"
git fetch

echo "git pull"
git pull

echo "python setup.py install"
cd /usr/local/src/ddr-cmdln/ddr
python setup.py install


echo "ddr-local"
cd /usr/local/src/ddr-local

echo "git fetch"
git fetch

echo "git pull"
git pull

echo "/etc/ddr/ddr.cfg"
cp /usr/local/src/ddr-local/debian/conf/ddr.cfg /etc/ddr/

mkdir /etc/ddr/templates

echo "/etc/ddr/templates/*"
cp /usr/local/src/ddr-local/debian/conf/templates/* /etc/ddr/templates/
chmod 644 /etc/ddr/templates/*

echo "./ddrlocal/ddrlocal/settings.py"
cp /usr/local/src/ddr-local/debian/conf/settings.py /usr/local/src/ddr-local/ddrlocal/ddrlocal

echo "/etc/nginx/sites-available/ddrlocal.conf"
cp /usr/local/src/ddr-local/debian/conf/ddrlocal.conf /etc/nginx/sites-available/

echo "/etc/supervisor/supervisord.conf"
cp /usr/local/src/ddr-local/debian/conf/supervisord.conf /etc/supervisor/


echo "/etc/supervisor/conf.d/celeryd.conf"
cp /usr/local/src/ddr-local/debian/conf/celeryd.conf /etc/supervisor/conf.d/

echo "/etc/supervisor/conf.d/gunicorn_ddrlocal.conf"
cp /usr/local/src/ddr-local/debian/conf/gunicorn_ddrlocal.conf /etc/supervisor/conf.d/

echo "supervisord restart"
/etc/init.d/supervisor restart

echo "supervisorctl status"
supervisorctl status

echo "/etc/init.d/nginx restart"
/etc/init.d/nginx restart

echo "/etc/init.d/elasticsearch restart"
/etc/init.d/elasticsearch restart
