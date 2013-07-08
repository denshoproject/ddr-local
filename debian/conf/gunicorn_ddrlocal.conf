[program:local]
user=www-data
directory=/opt/ddr-local/local
command=/opt/ddr-local/local/bin/env_run.sh /opt/ddr-local/virtualenv/bin/gunicorn_django -w 2 -b 0.0.0.0:8000
autostart=true
autorestart=true
redirect_stderr=True
