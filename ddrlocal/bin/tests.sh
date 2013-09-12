# Run unit tests
#

echo "[storage]"
./manage.py test storage
echo ""

echo "[ddrlocal]"
./manage.py test ddrlocal
echo ""

echo "[webui]"
./manage.py test webui
echo ""

