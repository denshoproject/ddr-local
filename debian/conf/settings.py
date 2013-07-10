# Django settings for ddrlocal.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# ----------------------------------------------------------------------

import ConfigParser
import os

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

# Keyword of the organization represented by this install.
DDR_ORGANIZATIONS    = config.get('local','organizations').split(',')

# Directory in root of USB HDD that marks it as a DDR disk
# /media/USBHDDNAME/ddr
# USBHDDNAME will be detected and git remotes will be named USBHDDNAME
DDR_USBHDD_BASE_DIR = 'ddr'

# path to SSH public key for the VM
DDR_SSHPUB_PATH      = config.get('local','ssh_pubkey')

# TODO replace with login user details
DDR_PROTOTYPE_USER   = config.get('testing','user_name')
DDR_PROTOTYPE_MAIL   = config.get('testing','user_mail')

STATIC_ROOT = '/var/www/ddrlocal/static'
STATIC_URL  = 'http://192.168.56.101/static/'

MEDIA_ROOT = '/var/www/ddr/'
MEDIA_URL  = 'http://192.168.56.101/media/'

# logging
WEBUI_LOG_FILE       = config.get('webui', 'log_file')
WEBUI_LOG_LEVEL      = config.get('webui', 'log_level')

ENTITY_FILE_ROLES = (
    ('master','master'),
    ('mezzanine','mezzanine'),
    ('access','access'),
)

REDIS_HOST = '127.0.0.1'
REDIS_PORT = '6379'
# REDIS_DB
# 0 - cache
# 1 - celery broker
# 2 - celery result

# ----------------------------------------------------------------------

import djcelery
djcelery.setup_loader()

ADMINS = (
    ('geoffrey jost', 'geoffrey.jost@densho.org'),
    #('Geoff Froh', 'geoff.froh@densho.org'),
)
MANAGERS = ADMINS

SITE_ID = 1
SECRET_KEY = 'N0~M0R3-53CR375'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    #
    'djcelery',
    #
    'storage',
    'webui',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/ddr-local/ddrlocal/ddrlocal.db',
    }
}

CACHES = {
    "default": {
        "BACKEND": "redis_cache.cache.RedisCache",
        "LOCATION": "127.0.0.1:6379:0",
        "OPTIONS": {
            "CLIENT_CLASS": "redis_cache.client.DefaultClient",
        }
    }
}

SESSION_ENGINE = 'redis_sessions.session'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'

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

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
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
    "progressbarupload.uploadhandler.ProgressBarUploadHandler",
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

# Celery
BROKER_URL            = 'redis://%s:%s/1' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_BACKEND = 'redis://%s:%s/2' % (REDIS_HOST, REDIS_PORT)
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 60 * 60}  # 1 hour
