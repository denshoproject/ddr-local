# Django settings for ddrlocal.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# ----------------------------------------------------------------------

from datetime import timedelta
import ConfigParser
import logging
import os

os.environ['USER'] = 'ddr'

class NoConfigError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

CONFIG_FILE = '/etc/ddr/ddr.cfg'
if not os.path.exists(CONFIG_FILE):
    raise NoConfigError('No config file!')
config = ConfigParser.ConfigParser()
config.read(CONFIG_FILE)

AGENT = 'ddr-local'

SECRET_KEY           = config.get('local','secret_key')
LANGUAGE_CODE        = config.get('local','language_code')
TIME_ZONE            = config.get('local','time_zone')
VIRTUALBOX_SHARED_FOLDER = config.get('local','virtualbox_shared_folder')
DDR_ORGANIZATIONS    = config.get('local','organizations').split(',')
DDR_SSHPUB_PATH      = config.get('local','ssh_pubkey')
DDR_PROTOTYPE_USER   = config.get('testing','user_name')
DDR_PROTOTYPE_MAIL   = config.get('testing','user_mail')
STATIC_ROOT          = config.get('local','static_root')
STATIC_URL           = config.get('local','static_url')
MEDIA_ROOT           = config.get('local','media_root')
MEDIA_URL            = config.get('local','media_url')
TEMPLATE_CJSON       = config.get('local','template_cjson')
TEMPLATE_EJSON       = config.get('local','template_ejson')
TEMPLATE_EAD         = config.get('local','template_ead')
TEMPLATE_METS        = config.get('local','template_mets')
ACCESS_FILE_APPEND   = config.get('local','access_file_append')
ACCESS_FILE_EXTENSION = config.get('local','access_file_extension')
ACCESS_FILE_GEOMETRY = config.get('local','access_file_geometry')
ACCESS_FILE_OPTIONS  = config.get('local','access_file_options')
THUMBNAIL_GEOMETRY   = config.get('local','thumbnail_geometry')
THUMBNAIL_COLORSPACE = 'sRGB'
THUMBNAIL_OPTIONS    = config.get('local','thumbnail_options')
DEFAULT_PERMISSION_COLLECTION = config.get('local','default_permission_collection')
DEFAULT_PERMISSION_ENTITY     = config.get('local','default_permission_entity')
DEFAULT_PERMISSION_FILE       = config.get('local','default_permission_file')
LOG_FILE             = config.get('local', 'log_file')
LOG_LEVEL            = config.get('local', 'log_level')
VOCAB_TERMS_URL      = config.get('local', 'vocab_terms_url')
CSV_TMPDIR           = '/tmp/ddr/csv'

GITOLITE             = config.get('workbench','gitolite')
CGIT_URL             = config.get('workbench','cgit_url')
GIT_REMOTE_NAME      = config.get('workbench','remote')
WORKBENCH_URL        = config.get('workbench','workbench_url')
WORKBENCH_LOGIN_URL  = config.get('workbench','workbench_login_url')
WORKBENCH_LOGOUT_URL = config.get('workbench','workbench_logout_url')
WORKBENCH_LOGIN_TEST = config.get('workbench','login_test_url')
WORKBENCH_USERINFO   = config.get('workbench','workbench_userinfo_url')
WORKBENCH_NEWCOL_URL = config.get('workbench','workbench_newcol_url')
WORKBENCH_NEWENT_URL = config.get('workbench','workbench_newent_url')

TESTING_USERNAME     = config.get('testing','username')
TESTING_PASSWORD     = config.get('testing','password')
TESTING_REPO         = config.get('testing','repo')
TESTING_ORG          = config.get('testing','org')
TESTING_CID          = config.get('testing','cid')
TESTING_EID          = config.get('testing','eid')
TESTING_ROLE         = config.get('testing','role')
TESTING_SHA1         = config.get('testing','sha1')
TESTING_DRIVE_LABEL  = config.get('testing','drive_label')
TESTING_CREATE       = int(config.get('testing','create'))

# Directory in root of USB HDD that marks it as a DDR disk
# /media/USBHDDNAME/ddr
DDR_USBHDD_BASE_DIR = 'ddr'

MEDIA_BASE = os.path.join(MEDIA_ROOT, 'base')


ENTITY_FILE_ROLES = (
    ('master','master'),
    ('mezzanine','mezzanine'),
    ('access','access'),
)

DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M:%S'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S:%f'
# Django uses a slightly different datetime format
DATETIME_FORMAT_FORM = '%Y-%m-%d %H:%M:%S'

PRETTY_DATE_FORMAT = '%d %B %Y'
PRETTY_TIME_FORMAT = '%I:%M %p'
PRETTY_DATETIME_FORMAT = '%d %B %Y, %I:%M %p'

# cache key used for storing URL of page user was requesting
# when redirected to either login or storage remount page
REDIRECT_URL_SESSION_KEY = 'remount_redirect_uri'

REPOS_ORGS_TIMEOUT = 60*30 # 30min

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
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    #
    'bootstrap_pagination',
    'djcelery',
    'gunicorn',
    'sorl.thumbnail',
    #
    'ddrlocal',
    'storage',
    'webui',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/var/lib/ddr/ddrlocal.db',
    }
}

REDIS_HOST = '127.0.0.1'
REDIS_PORT = '6379'
REDIS_DB_CACHE = 0
REDIS_DB_CELERY_BROKER = 1
REDIS_DB_CELERY_RESULT = 2
REDIS_DB_SORL = 3

CACHES = {
    "default": {
        "BACKEND": "redis_cache.cache.RedisCache",
        "LOCATION": "%s:%s:%s" % (REDIS_HOST, REDIS_PORT, REDIS_DB_CACHE),
        "OPTIONS": {
            "CLIENT_CLASS": "redis_cache.client.DefaultClient",
        }
    }
}

# celery
CELERY_TASKS_SESSION_KEY = 'celery-tasks'
CELERY_RESULT_BACKEND = 'redis://%s:%s/%s' % (REDIS_HOST, REDIS_PORT, REDIS_DB_CELERY_RESULT)
BROKER_URL            = 'redis://%s:%s/%s' % (REDIS_HOST, REDIS_PORT, REDIS_DB_CELERY_BROKER)
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 60 * 60}  # 1 hour
CELERYD_HIJACK_ROOT_LOGGER = False
CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERYBEAT_PIDFILE = '/tmp/celerybeat.pid'
CELERYBEAT_SCHEDULE = {
    'webui-git-status': {
        'task': 'webui.tasks.gitstatus_update',
        'schedule': timedelta(seconds=60),
    },
}

# ElasticSearch
DOCSTORE_HOSTS = [
    {'host':'192.168.56.101', 'port':9200}
]
DOCSTORE_INDEX = 'documents0'
RESULTS_PER_PAGE = 20

# sorl-thumbnail
THUMBNAIL_DEBUG = DEBUG
#THUMBNAIL_DEBUG = False
THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.redis_kvstore.KVStore'
#THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.cached_db_kvstore.KVStore'
THUMBNAIL_REDIS_PASSWORD = ''
THUMBNAIL_REDIS_HOST = REDIS_HOST
THUMBNAIL_REDIS_PORT = int(REDIS_PORT)
THUMBNAIL_REDIS_DB = REDIS_DB_SORL
THUMBNAIL_ENGINE = 'sorl.thumbnail.engines.convert_engine.Engine'
THUMBNAIL_CONVERT = 'convert'
THUMBNAIL_IDENTIFY = 'identify'
THUMBNAIL_CACHE_TIMEOUT = 60*60*24*365*10  # 10 years

SESSION_ENGINE = 'redis_sessions.session'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

TEMPLATE_DIRS = (
    '/usr/local/src/ddr-local/ddrlocal/ddrlocal/templates',
    '/usr/local/src/ddr-local/ddrlocal/storage/templates',
    '/usr/local/src/ddr-local/ddrlocal/webui/templates',
)

STATICFILES_DIRS = (
    #'/opt/ddr-local/ddrlocal/ddrlocal/static',
    #'/usr/local/src/ddr-local/ddrlocal/storage/static',
    '/usr/local/src/ddr-local/ddrlocal/webui/static',
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
            '()': 'webui.log.SuppressCeleryNewConnections'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
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

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'storage.context_processors.sitewide',
    'webui.context_processors.sitewide',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'ddrlocal.urls'

WSGI_APPLICATION = 'ddrlocal.wsgi.application'
