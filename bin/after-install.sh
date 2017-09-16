# Add symlinks after installing (FPM) .deb package

# nginx: install ddrlocal.conf, rm nginx default
if [ ! -f /etc/nginx/sites-enabled/ddrlocal.conf ]
then
    ln -s /etc/nginx/sites-available/ddrlocal.conf /etc/nginx/sites-enabled/ddrlocal.conf
fi
if [ -f /etc/nginx/sites-enabled/default ]
then
    rm /etc/nginx/sites-enabled/default
fi

# logs dir perms
mkdir -p /var/log/ddr
chmod 755 /var/log/ddr
chown -R ddr.ddr /var/log/ddr

# sqlite3 database dir perms
mkdir -p /var/lib/ddr
chmod 755 /var/lib/ddr
chown -R ddr.ddr /var/lib/ddr

# static dir symlinks

if [ ! -f /var/www/static/bootstrap ]
then
    ln -s /var/www/static/bootstrap-3.1.1-dist /var/www/static/bootstrap
fi

if [ ! -f /var/www/static/js/jquery.js ]
then
    ln -s /var/www/static/js/jquery-1.11.0.min.js /var/www/static/js/jquery.js
fi

if [ ! -f /var/www/static/js/modernizr.js ]
then
    ln -s /var/www/static/js/modernizr-2.6.2.js /var/www/static/js/modernizr.js
fi

if [ ! -f /var/www/static/js/tagmanager ]
then
    ln -s /var/www/static/tagmanager-3.0.1 /var/www/static/js/tagmanager
fi

if [ ! -f /var/www/static/js/typeahead ]
then
    ln -s /var/www/static/typeahead-0.10.2 /var/www/static/js/typeahead
fi
