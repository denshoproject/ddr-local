from django import forms
from django.conf import settings



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
        'form_type':  forms.ChoiceField,
        'form': {
            'label':      'Privacy Level',
            'help_text':  'Setting applies permission to everything under this object.',
            'widget':     '',
            'choices':    PERMISSIONS_CHOICES,
            'initial':    settings.DEFAULT_PERMISSION_COLLECTION,
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
        'form_type':  forms.IntegerField,
        'form': {
            'label':      'Sort',
            'help_text':  '',
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
        'form_type':  forms.IntegerField,
        'form': {
            'label':      'Thumbnail',
            'help_text':  '',
            'widget':     forms.HiddenInput,
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
        'form_type':  forms.CharField,
        'form': {
            'label':      'Label',
            'help_text':  '',
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
        'form_type':  forms.CharField,
        'form': {
            'label':      'XMP Metadata',
            'help_text':  '',
            'widget':     forms.HiddenInput,
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
        'form_type':  forms.CharField,
        'form': {
            'label':      'Associated Files',
            'help_text':  'Semicolon-separated list of file.path_rels that this file points to.',
            'max_length': 255,
            'widget':     forms.Textarea,
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
