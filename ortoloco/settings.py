# -*- coding: utf-8 -*-

# Django settings for ortoloco project.
import os
import sys

print('---------- in settings.py ------------')
# this is custom code to detect differentiate different servers and use 
# as little stuff in settings_local.py as necessary
if "ortho" == os.environ.get("OPENSHIFT_GEAR_NAME"):
    TARGET = 'production'
    # todo - so far everything is debug...
    DEBUG = True
elif "test" == os.environ.get("OPENSHIFT_GEAR_NAME"):
    TARGET = 'test'
    DEBUG = True
else:
    TARGET = 'local'
    DEBUG = True
    
if 'local' == TARGET:
    # accept all IPs from local network and show admin toolbar    
    from fnmatch import fnmatch
    class glob_list(list):
        def __contains__(self, key):
            for elt in self:
                if fnmatch(key, elt): return True
            return False

    INTERNAL_IPS = glob_list(['127.0.0.1', '192.168.*.*'])
    DEBUG_TOOLBAR_PATCH_SETTINGS = True
    # use an SQlite DB 
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3', 
            'NAME': 'bioco.db.sqlite',
            # The following settings are not used with sqlite3:
            'USER': '', 
            'PASSWORD': '',
            'HOST': '', 
            'PORT': '', 
        }
    }
else:
    # on openshift
    DEBUG_TOOLBAR_PATCH_SETTINGS = False
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql', 
            'NAME': os.environ.get("OPENSHIFT_GEAR_NAME"), 
            'USER': os.environ.get("OPENSHIFT_MYSQL_DB_USERNAME"), 
            'PASSWORD': os.environ.get("OPENSHIFT_MYSQL_DB_PASSWORD"),
            'HOST': os.environ.get("OPENSHIFT_MYSQL_DB_HOST"), 
            'PORT': os.environ.get("OPENSHIFT_MYSQL_DB_PORT"), 
        }
    }
    
#TODO TLS times out on bioco.ch, investigate why and change to True
EMAIL_USE_TLS = False
if EMAIL_USE_TLS:
    EMAIL_PORT = 465
else:
    EMAIL_PORT = 587
EMAIL_HOST = 'mail.bioco.ch'
EMAIL_HOST_USER = 'test@bioco.ch'
EMAIL_HOST_PASSWORD = 'to-be-set-in-settings_local'  
    
TEMPLATE_DEBUG = DEBUG

# Overwrite these in settings_local.py to prevent having raw emails in GIT:
WHITELIST_EMAILS = []
ADMINS = (
# ('Your Name', 'your_email@example.com'),
)

# let the users login with their emails
AUTHENTICATION_BACKENDS = (
    'my_ortoloco.helpers.AuthenticateWithEmail',
    'django.contrib.auth.backends.ModelBackend'
)

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['intranet.bioco.ch']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Zurich'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'de_CH'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'static/medias/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/medias/'



# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

if 'local' == TARGET:
    # ./static contains checked in static content
    STATICFILES_DIRS = ("static/",)
    # collectstatic will want to move it to a *different folder*, here:
    STATIC_ROOT = os.path.join(BASE_DIR, 'static_collected/')    
else:
    # this has worked in production:
    
    # Absolute path to the directory static files should be collected to.
    # Don't put anything in this directory yourself; store your static files
    # in apps' "static/" subdirectories and in STATICFILES_DIRS.
    # Example: "/var/www/example.com/static/"
    STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

    # Additional locations of static files
    STATICFILES_DIRS = (
    #"static/",
    #os.path.join(BASE_DIR, 'ortoloco/static/'),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    )

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #mbs+
    #'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

#tinyMCE
TINYMCE_JS_URL = '/static/js/tinymce/tinymce.min.js'

TINYMCE_DEFAULT_CONFIG = {
    'theme': "modern",
    'plugins': 'link',
    'relative_urls': False,
    'valid_styles': {
        '*': 'color,text-align,font-size,font-weight,font-style,text-decoration'
    },
    'menu': {
        'edit': {
            'title': 'Edit',
            'items': 'undo redo | cut copy paste | selectall'
        },
        'insert': {
            'title': 'Insert',
            'items': 'link'
        },
        'format': {
            'title': 'Format',
            'items': 'bold italic underline strikethrough superscript subscript | formats | removeformat'
        }
    }
}

# Make this unique, and don't share it with anybody.
# set in settings_local.py
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
	#mbs (maybe not required)?
    #'django.template.loaders.eggs.Loader',
)

IMPERSONATE_REDIRECT_URL = "/my/profil"

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'impersonate.middleware.ImpersonateMiddleware'
)

ROOT_URLCONF = 'ortoloco.urls'

# Python dotted path to the WSGI application used by Django's runserver.
# this seems to be used only for testing with runserver 
WSGI_APPLICATION = 'ortoloco.wsgi.application'

#mbs disabled photologue for now:
#from photologue import PHOTOLOGUE_TEMPLATE_DIR

TEMPLATE_DIRS = (
    'ortoloco/templates',
	os.path.join(BASE_DIR, 'ortoloco/templates'),
    #mbs disabled photologue for now:
    #PHOTOLOGUE_TEMPLATE_DIR
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

DJANGO_APPS = (
    'django_cron',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Serves static files through pyton in dev-mode
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
)
DEBUG_APPS = (
    # Uncomment the next line to enable admin documentation:
    'django.contrib.admindocs',	
    'debug_toolbar',
)
OUR_OWN_APPS = (
	'my_ortoloco',
	'static_ortoloco',
    # mbs - Currently disabled 
	#'photologue',
	'south',
	'tinymce',
	'impersonate'
)
if 'local' == TARGET:
    INSTALLED_APPS = DJANGO_APPS + DEBUG_APPS + OUR_OWN_APPS
else:
    INSTALLED_APPS = DJANGO_APPS + OUR_OWN_APPS
# For the first syncdb, use only
#INSTALLED_APPS = DJANGO_APPS

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'ortoloco.ch_python.log': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(os.path.dirname(BASE_DIR), '../logs/ortoloco.ch_python.log'),
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['ortoloco.ch_python.log'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

GALLERY_SAMPLE_SIZE = 4
 
# add persistent data dir where settings_local.py is located
if 'local' == TARGET:
    # add path as needed:
    pass
else:    
    #on openshift:
    sys.path.append(os.environ.get("OPENSHIFT_DATA_DIR"))

# This is a custom variable to replace ortoloco with bioco in templates and co.
SITE_NAME = u'biocò'
SITE_URL  = u'bioco.ch'
SITE_MY_NAME = u'biocò Intranet'
SITE_MY_URL  = u'intranet.bioco.ch'
LINK_REL_STATUTEN = u'http://bioco.ch/wp-content/uploads/2013/11/13-11-15_Statuten_bioco.pdf'
LINK_REL_REGLEMENT = u'http://bioco.ch/wp-content/uploads/2013/11/Gm%C3%BCes_Betriebsreglement_131114a.pdf'

""" 
Note: Currently settings_local.py should have the following content.

WHITELIST_EMAILS = ["...@..."]
ADMINS = (
	('xxx', '...@...'),
)
SECRET_KEY = 'a long random string. Shhh keep it secret!'
EMAIL_HOST_PASSWORD = '...'
DEBUG_EMAIL_ADDRESS = '...'
"""

from settings_local import *

# overwrite from settings_local if set there
MANAGERS = ADMINS
