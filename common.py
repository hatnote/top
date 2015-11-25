# -*- coding: utf-8 -*-

import os
from os.path import dirname, join as pjoin

# Settings
DEBUG = True


# Files and locations
_CUR_PATH = dirname(os.path.abspath(__file__))
_BASE_PATH = pjoin(_CUR_PATH, 'static')
DATA_FILE_TMPL = '{lang}{project}/{year}/{month}/{day}.json'
DATA_PATH_TMPL = pjoin(_BASE_PATH, DATA_FILE_TMPL)
HTML_BASE_PATH = pjoin(_CUR_PATH, 'static')
HTML_FILE_TMPL = '{lang}{project}/{year}/{month}/{day}.html'
HTML_PATH_TMPL = pjoin(_BASE_PATH, HTML_FILE_TMPL)


# Valuable and important URLs
TOP_API_URL = 'https://wikimedia.org/api/rest_v1/metrics/pageviews/'\
              'top/{lang}.{project}/all-access/{year}/{month}/{day}'
MW_API_URL = 'https://{lang}.{project}.org/w/api.php?'

# Other variables
LOCAL_LANG_MAP = {'en': u'English',
                  'de': u'Deutsch',
                  'fr': u'Français',
                  'ko': u'한국어',
                  'et': u'Eesti',
                  'sv': u'Svenska',
                  'da': u'Dansk',
                  'it': u'Italiano',
                  'ca': u'Català',
                  'es': u'Español',
                  'fa': u'فارسی',
                  'ur': u'اردو',
                  'zh': u'中文',
                  'kn': u'ಕನ್ನಡ'}
DEFAULT_LANG = 'en'
DEFAULT_PROJECT = 'wikipedia'

# These prefixes are not for articles
PREFIXES = ['Special', 'Template', 'Sp?cial', 'Project']
