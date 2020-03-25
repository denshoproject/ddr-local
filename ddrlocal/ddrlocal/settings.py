"""
Django settings for ddrlocal project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# ----------------------------------------------------------------------

DEBUG = True

from datetime import timedelta
import logging
import sys

import pytz

# import all settings from ddr-cmdln DDR/config.py
# including the ConfigParser object CONFIG
from DDR.config import *

os.environ['USER'] = 'ddr'

AGENT = 'ddr-local'

# Latest commits for ddr-cmdln and ddr-local.
# Include here in settings so only has to be retrieved once,
# and so commits are visible in error pages and in page footers.
from DDR import dvcs
dvcs.APP_COMMITS['loc'] = dvcs.latest_commit(os.path.dirname(__file__))
APP_COMMITS_HTML = '<br/>\n'.join([
    'loc: %s' % dvcs.APP_COMMITS['loc'],
    'cmd: %s' % dvcs.APP_COMMITS['cmd'],
    'def: %s' % dvcs.APP_COMMITS['def'],
    'def: %s' % REPO_MODELS_PATH,
])

# The following settings are in debian/config/ddr.cfg.
# See that file for comments on the settings.
# ddr.cfg is installed in /etc/ddr/ddr.cfg.
# Settings in /etc/ddr/ddr.cfg may be overridden in /etc/ddr/local.cfg.

GITOLITE             = CONFIG.get('workbench','gitolite')
GITOLITE_TIMEOUT     = CONFIG.get('workbench','gitolite_timeout')
CGIT_URL             = CONFIG.get('workbench','cgit_url')
GIT_REMOTE_NAME      = CONFIG.get('workbench','remote')
IDSERVICE_API_BASE   = CONFIG.get('cmdln', 'idservice_api_base')

GITWEB_URL           = CONFIG.get('local','gitweb_url')
SUPERVISORD_URL      = CONFIG.get('local','supervisord_url')
SUPERVISORD_PROCS    = ['ddrlocal', 'celery']
SECRET_KEY           = CONFIG.get('local','secret_key')
LANGUAGE_CODE        = CONFIG.get('local','language_code')
TIME_ZONE            = CONFIG.get('local','time_zone')
VIRTUALBOX_SHARED_FOLDER = CONFIG.get('local','virtualbox_shared_folder')
DDR_ORGANIZATIONS    = CONFIG.get('local','organizations').split(',')
DDR_SSHPUB_PATH      = CONFIG.get('local','ssh_pubkey')
DDR_PROTOTYPE_USER   = CONFIG.get('testing','user_name')
DDR_PROTOTYPE_MAIL   = CONFIG.get('testing','user_mail')
STATIC_ROOT          = CONFIG.get('local','static_root')
STATIC_URL           = CONFIG.get('local','static_url')
MEDIA_ROOT           = CONFIG.get('local','media_root')
MEDIA_URL            = CONFIG.get('local','media_url')
DEFAULT_PERMISSION_COLLECTION = CONFIG.get('local','default_permission_collection')
DEFAULT_PERMISSION_ENTITY     = CONFIG.get('local','default_permission_entity')
DEFAULT_PERMISSION_FILE       = CONFIG.get('local','default_permission_file')
LOG_DIR              = CONFIG.get('local', 'log_dir')
LOG_FILE             = CONFIG.get('local', 'log_file')
LOG_LEVEL            = CONFIG.get('local', 'log_level')
CSV_EXPORT_PATH = {
    'entity': '/tmp/ddr/csv/%s-objects.csv',
    'file': '/tmp/ddr/csv/%s-files.csv',
}

# Display (or not) list of remotes where file present
GIT_ANNEX_WHEREIS = CONFIG.getboolean('local','git_annex_whereis')

# ElasticSearch
DOCSTORE_ENABLED     = CONFIG.getboolean('local','docstore_enabled')
ds_host,ds_port      = CONFIG.get('local', 'docstore_host').split(':')
DOCSTORE_HOSTS = [
    {'host':ds_host, 'port':ds_port}
]
DOCSTORE_TIMEOUT     = int(CONFIG.get('local', 'docstore_timeout'))
RESULTS_PER_PAGE = 25
ELASTICSEARCH_MAX_SIZE = 10000
ELASTICSEARCH_DEFAULT_LIMIT = RESULTS_PER_PAGE

GITOLITE_INFO_CACHE_TIMEOUT = int(CONFIG.get('local', 'gitolite_info_cache_timeout'))
GITOLITE_INFO_CACHE_CUTOFF  = int(CONFIG.get('local', 'gitolite_info_cache_cutoff'))
GITOLITE_INFO_CHECK_PERIOD  = int(CONFIG.get('local', 'gitolite_info_check_period'))

TESTING_USERNAME     = CONFIG.get('testing','username')
TESTING_PASSWORD     = CONFIG.get('testing','password')
TESTING_REPO         = CONFIG.get('testing','repo')
TESTING_ORG          = CONFIG.get('testing','org')
TESTING_CID          = CONFIG.get('testing','cid')
TESTING_EID          = CONFIG.get('testing','eid')
TESTING_ROLE         = CONFIG.get('testing','role')
TESTING_SHA1         = CONFIG.get('testing','sha1')
TESTING_DRIVE_LABEL  = CONFIG.get('testing','drive_label')
TESTING_CREATE       = int(CONFIG.get('testing','create'))

# Directory in root of USB HDD that marks it as a DDR disk
# /media/USBHDDNAME/ddr
DDR_USBHDD_BASE_DIR = 'ddr'

ENTITY_FILE_ROLES = (
    ('master','master'),
    ('mezzanine','mezzanine'),
    ('access','access'),
)

# Django uses a slightly different datetime format
DATETIME_FORMAT_FORM = '%Y-%m-%d %H:%M:%S'

# cache key used for storing URL of page user was requesting
# when redirected to either login or storage remount page
REDIRECT_URL_SESSION_KEY = 'remount_redirect_uri'

REPOS_ORGS_TIMEOUT = 60*30 # 30min

GITSTATUS_LOG = '/var/log/ddr/gitstatus.log'
# File used to manage queue for gitstatus-update
GITSTATUS_QUEUE_PATH = os.path.join(MEDIA_BASE, '.gitstatus-queue')
# Processes that should not be interrupted by gitstatus-update should
# write something to this file (doesn't matter what) and remove the file
# when they are finished.
GITSTATUS_LOCK_PATH = os.path.join(MEDIA_BASE, '.gitstatus-stop')
# Normally a global lockfile allows only a single gitstatus process at a time.
# To allow multiple processes (e.g. multiple VMs using a shared storage device),
# add the following setting to /etc/ddr/local.cfg:
#     gitstatus_use_global_lock=0
GITSTATUS_USE_GLOBAL_LOCK = True
if CONFIG.has_option('local', 'gitstatus_use_global_lock'):
    GITSTATUS_USE_GLOBAL_LOCK = CONFIG.get('local', 'gitstatus_use_global_lock')
# Minimum interval between git-status updates per collection repository.
GITSTATUS_INTERVAL = 60*60*1
GITSTATUS_BACKOFF = 30
# Indicates whether or not gitstatus_update_store periodic task is active.
# This should be True for most single-user workstations.
# See CELERYBEAT_SCHEDULE below.
# IMPORTANT: If disabling GITSTATUS, also remove the celerybeat config file
# and restart supervisord:
#   $ sudo supervisorctl stop celerybeat
#   $ sudo rm /etc/supervisor/conf.d/celerybeat.conf
#   $ sudo supervisorctl reload
GITSTATUS_BACKGROUND_ACTIVE = True
if CONFIG.has_option('local', 'gitstatus_background_active'):
    GITSTATUS_BACKGROUND_ACTIVE = CONFIG.getboolean('local', 'gitstatus_background_active')
    SUPERVISORD_PROCS.append('celerybeat')

MANUAL_URL = os.path.join(MEDIA_URL, 'manual')

# ----------------------------------------------------------------------

import djcelery
djcelery.setup_loader()

ADMINS = (
    ('geoffrey jost', 'geoffrey.jost@densho.org'),
    #('Geoff Froh', 'geoff.froh@densho.org'),
)
MANAGERS = ADMINS

SITE_ID = 1

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #
    'bootstrap_pagination',
    'djcelery',
    'gunicorn',
    'rest_framework',
    'sorl.thumbnail',
    #
    'ddrlocal',
    'storage',
    'webui',
)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'PAGE_SIZE': 20
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/var/lib/ddr/ddrlocal.db',
    }
}

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB_CACHE = 0
REDIS_DB_CELERY_BROKER = 1
REDIS_DB_CELERY_RESULT = 2
REDIS_DB_SORL = 3

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{}:{}/{}".format(
            REDIS_HOST, str(REDIS_PORT), str(REDIS_DB_CACHE)
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# celery
CELERY_TASKS_SESSION_KEY = 'celery-tasks'
CELERY_RESULT_BACKEND = 'redis://{}:{}/{}'.format(
    REDIS_HOST, str(REDIS_PORT), str(REDIS_DB_CELERY_RESULT)
)
BROKER_URL            = 'redis://{}:{}/{}'.format(
    REDIS_HOST, str(REDIS_PORT), str(REDIS_DB_CELERY_BROKER)
)
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 60 * 60}  # 1 hour
CELERYD_HIJACK_ROOT_LOGGER = False
CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']
CELERYBEAT_SCHEDULER = None
CELERYBEAT_PIDFILE = None
CELERYBEAT_SCHEDULE = {
    'webui-gitolite-info-refresh': {
        'task': 'webui.tasks.gitolite_info_refresh',
        'schedule': timedelta(seconds=GITOLITE_INFO_CHECK_PERIOD),
    }
}
if GITSTATUS_BACKGROUND_ACTIVE:
    CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
    CELERYBEAT_PIDFILE = '/tmp/celerybeat.pid'
    CELERYBEAT_SCHEDULE['webui-git-status-update-store'] = {
        'task': 'webui.tasks.gitstatus_update_store',
        'schedule': timedelta(seconds=60),
    }

# sorl-thumbnail
THUMBNAIL_DEBUG = DEBUG
#THUMBNAIL_DEBUG = False
THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.dbm_kvstore.KVStore'
THUMBNAIL_DBM_FILE = CONFIG.get('local', 'thumbnail_dbm_file')
THUMBNAIL_ENGINE = 'sorl.thumbnail.engines.convert_engine.Engine'
THUMBNAIL_CONVERT = 'convert'
THUMBNAIL_IDENTIFY = 'identify'
THUMBNAIL_CACHE_TIMEOUT = 60*60*24*365*10  # 10 years
THUMBNAIL_DUMMY = True
# Thumbnail dummy (placeholder) source. Some you might try are:
# http://placekitten.com/%(width)s/%(height)s
# http://placekitten.com/g/%(width)s/%(height)s
# http://placehold.it/%(width)sx%(height)s
THUMBNAIL_DUMMY_SOURCE = 'http://dummyimage.com/%(width)sx%(height)s'
# Sets source image ratio for dummy images w only width or height
THUMBNAIL_DUMMY_RATIO = 1.5

SESSION_ENGINE = 'redis_sessions.session'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    host.strip()
    for host in CONFIG.get('local', 'allowed_hosts').split(',')
]

STATICFILES_DIRS = (
    #os.path.join(BASE_DIR, 'storage/static'),
    os.path.join(BASE_DIR, 'webui/static'),
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)-8s [%(module)s.%(funcName)s]  %(message)s'
        },
        'simple': {
            'format': '%(asctime)s %(levelname)-8s %(message)s'
        },
    },
    'filters': {
        # only log when settings.DEBUG == False
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'suppress_celery_newconnect': {
            # NOTE: Import problems here may indicate problems in the definitions
            # modules, such as a syntax error or a missing dependency (e.g. lxml).
            # They may also indicate an import problem elsewhere.
            '()': 'webui.log.SuppressCeleryNewConnections'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': LOG_FILE,
            'when': 'D',
            'backupCount': 14,
            'filters': ['suppress_celery_newconnect'],
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.request': {
            'level': 'ERROR',
            'propagate': True,
            'handlers': ['mail_admins'],
        },
    },
    # This is the only way I found to write log entries from the whole DDR stack.
    'root': {
        'level': 'DEBUG',
        'handlers': ['file'],
    },
}

USE_TZ = True
USE_I18N = True
USE_L10N = True

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

FILE_UPLOAD_HANDLERS = (
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'ddrlocal/templates'),
            os.path.join(BASE_DIR, 'storage/templates'),
            os.path.join(BASE_DIR, 'webui/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'webui.context_processors.sitewide',
            ],
        },
    },
]
                                                                        
MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

ROOT_URLCONF = 'ddrlocal.urls'

WSGI_APPLICATION = 'ddrlocal.wsgi.application'
