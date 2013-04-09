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
GITOLITE = config.get('workbench','gitolite')
GIT_REMOTE_NAME = config.get('workbench','remote')

DDR_REPOSITORY = config.get('local','repository')
# Keyword of the organization represented by this install.
DDR_ORGANIZATION = config.get('local','organization')
DDR_ORG_UID = '{}-{}'.format(DDR_REPOSITORY, DDR_ORGANIZATION)

# Base path to dir where the repos go
LOCAL_BASE_PATH = config.get('local','base_path')
DDR_BASE_PATH = os.path.join(LOCAL_BASE_PATH, DDR_ORG_UID)

# Directory in root of USB HDD that marks it as a DDR disk
# /media/USBHDDNAME/ddr
# USBHDDNAME will be detected and git remotes will be named USBHDDNAME
DDR_USBHDD_BASE_DIR = DDR_ORG_UID

# path to SSH public key for the VM
DDR_SSHPUB_PATH = config.get('local','ssh_pubkey')

# TODO replace with login user details
DDR_PROTOTYPE_USER = config.get('testing','user_name')
DDR_PROTOTYPE_MAIL = config.get('testing','user_mail')

# ----------------------------------------------------------------------

ADMINS = (
    ('geoffrey jost', 'geoffrey.jost@densho.org'),
)
MANAGERS = ADMINS

SITE_ID = 1
SECRET_KEY = '2a&29e10pd!(1p16oaj57rpxg%f!*u88p!1gl6sy*=2z_h!o(e'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/home/gjost/ddr-local/ddrlocal/ddrlocal.db',
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'

TEMPLATE_DIRS = (
    '/home/gjost/ddr-local/ddrlocal/ddrlocal/templates',
)

STATICFILES_DIRS = (
    '/home/gjost/ddr-local/ddrlocal/ddrlocal/static',
)
STATIC_ROOT = ''
STATIC_URL = '/static/'

MEDIA_ROOT  = ''
MEDIA_URL  = ''

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

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'webui',
)

USE_TZ = True
USE_I18N = True
USE_L10N = True

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
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
