# Do things after installing (FPM) .deb package

# add ddr user
groupadd --gid 1001 ddr
useradd --gid 1001 --uid 1001 --shell /bin/bash --create-home --home-dir /home/ddr ddr
adduser ddr plugdev

# settings files
chown root:root /etc/ddr/ddrlocal.cfg
chmod 644       /etc/ddr/ddrlocal.cfg
touch           /etc/ddr/ddrlocal-local.cfg
chown ddr:root  /etc/ddr/ddrlocal-local.cfg
chmod 640       /etc/ddr/ddrlocal-local.cfg

# nginx: install ddrlocal.conf, rm nginx default
if [ ! -f /etc/nginx/sites-enabled/ddrlocal.conf ]
then
    ln -s /etc/nginx/sites-available/ddrlocal.conf /etc/nginx/sites-enabled/ddrlocal.conf
fi
if [ -f /etc/nginx/sites-enabled/default ]
then
    rm /etc/nginx/sites-enabled/default
fi

# logs dir
mkdir -p /var/log/ddr
chmod 755 /var/log/ddr
chown -R ddr:ddr /var/log/ddr

# sqlite3 database dir
mkdir -p /var/lib/ddr
chmod 755 /var/lib/ddr
chown -R ddr:ddr /var/lib/ddr

# thumbnails dir
mkdir -p /var/www/media/cache
chmod 755 /var/www/media/cache
chown -R ddr:ddr /var/www/media/cache

# Install customized ImageMagick-6/policy.xml.  This disables default
# memory and cache limits put in place to protect against DDoS attacks
# but these are not an issue in our local install.
echo "Installing custom Imagemagick policy.xml"
# Release name e.g. jessie
DEBIAN_CODENAME=$(lsb_release -sc)
if [ $DEBIAN_CODENAME = 'bullseye' ]
then
    cp /opt/ddr-cmdln/conf/imagemagick-policy.xml.deb11 /etc/ImageMagick-6/policy.xml
fi
if [ $DEBIAN_CODENAME = 'bookworm' ]
then
    cp /opt/ddr-cmdln/conf/imagemagick-policy.xml.deb12 /etc/ImageMagick-6/policy.xml
fi
