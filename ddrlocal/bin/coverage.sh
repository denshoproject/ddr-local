# Generates code coverage reports for ddr-local apps
#
# INSTALL
# $ pip install -r requirements/dev.txt
#

YYYYMMDD=`date +"%Y%m%d-%H%M"`
OUT=coverage-$YYYYMMDD

echo "coverage $YYYYMMDD" > $OUT
echo "" >> $OUT

echo "[storage]" >> $OUT
coverage run --source='./storage' manage.py test storage
coverage report -m >> $OUT
echo "" >> $OUT

echo "[ddrlocal]" >> $OUT
coverage run --source='./ddrlocal' manage.py test ddrlocal
coverage report -m >> $OUT
echo "" >> $OUT

echo "[webui]" >> $OUT
coverage run --source='./webui' manage.py test webui
coverage report -m >> $OUT
echo "" >> $OUT

