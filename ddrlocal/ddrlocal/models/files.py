import logging
logger = logging.getLogger(__name__)



DEFAULT_PERMISSION_COLLECTION = 1

DATE_FORMAT            = '%Y-%m-%d'
TIME_FORMAT            = '%H:%M:%S'
DATETIME_FORMAT        = '%Y-%m-%dT%H:%M:%S'
PRETTY_DATE_FORMAT     = '%d %B %Y'
PRETTY_TIME_FORMAT     = '%I:%M %p'
PRETTY_DATETIME_FORMAT = '%d %B %Y, %I:%M %p'

PERMISSIONS_CHOICES = [['1','public'],
                       ['0','private'],]



FILE_FIELDS = [
    {
        'name':       'sha1',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        # no form_type
        # no form
        'default':    '',
    },
    {
        'name':       'sha256',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        # no form_type
        # no form
        'default':    '',
    },
    {
        'name':       'md5',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        # no form_type
        # no form
        'default':    '',
    },
    {
        'name':       'size',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        # no form_type
        # no form
        'default':    '',
    },
    {
        'name':       'basename_orig',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        # no form_type
        # no form
        'default':    '',
    },
    {
        'name':       'access_rel',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        # no form_type
        # no form
        'default':    '',
    },
    {
        'name':       'public',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': int,
        'form_type':  'ChoiceField',
        'form': {
            'label':      'Privacy Level',
            'help_text':  'Whether this file should be accessible from the public website.',
            'widget':     '',
            'choices':    PERMISSIONS_CHOICES,
            'initial':    DEFAULT_PERMISSION_COLLECTION,
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'sort',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': int,
        'form_type':  'IntegerField',
        'form': {
            'label':      'Sort',
            'help_text':  'Order of this file in relation to others for this object (ordered low to high). Can be used to arrange images in a multi-page document.',
            'widget':     '',
            'initial':    1,
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'thumb',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': int,
        'form_type':  'IntegerField',
        'form': {
            'label':      'Thumbnail',
            'help_text':  '',
            'widget':     'HiddenInput',
            'initial':    -1,
            'required':   True,
        },
        'default':    '',
    },
    {
        'name':       'label',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Label',
            'help_text':  '(Optional) Friendly label for file describing partitive role (i.e., \"Page 1\", \"Cover\", \"Envelope\")',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'xmp',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'XMP Metadata',
            'help_text':  '',
            'widget':     'HiddenInput',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'links',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  'CharField',
        'form': {
            'label':      'Associated Files',
            'help_text':  'Semicolon-separated list of file.path_rels that this file points to.',
            'max_length': 255,
            'widget':     'HiddenInput',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
]



# display_* --- Display functions --------------------------------------
#
# These functions take Python data from the corresponding Collection field
# and format it for display.
#

def display_public( data ):
    for c in PERMISSIONS_CHOICES:
        if data == c[0]:
            return c[1]
    return data

def display_sort( data ):
    return ''

def display_thumb( data ):
    return ''

def display_xmp( data ):
    return ''

def display_links( data ):
    return ''



# formprep_* --- Form pre-processing functions.--------------------------
#
# These functions take Python data from the corresponding Collection field
# and format it so that it can be used in an HTML form.
#



# formpost_* --- Form post-processing functions ------------------------
#
# These functions take data from the corresponding form field and turn it
# into Python objects that are inserted into the Collection.
#
