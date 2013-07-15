# update.sh - Pulls down new code, copies configs, restarts
#
# NOTE: This script is meant to be run from the ddr-local/ddrlocal dir.
# NOTE: Does not flush caches.

echo "git fetch"
git fetch

echo "git pull"
git pull

echo "/etc/ddr/ddr.cfg"
sudo cp ../debian/conf/ddr.cfg /etc/ddr/

echo "./ddrlocal/ddrlocal/settings.py"
cp ../debian/conf/settings.py ./ddrlocal/

echo "/etc/nginx/sites-available/ddrlocal.conf"
sudo cp ../debian/conf/ddrlocal.conf /etc/nginx/sites-available/

echo "/etc/supervisor/conf.d/gunicorn_ddrlocal.conf"
sudo cp ../debian/conf/gunicorn_ddrlocal.conf /etc/supervisor/conf.d/

echo "supervisorctl reload"
sudo supervisorctl reload

echo "supervisorctl restart ddrlocal"
sudo supervisorctl restart ddrlocal

echo "/etc/init.d/nginx restart"
sudo /etc/init.d/nginx restart


