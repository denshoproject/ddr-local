from django import forms
from django.conf import settings



FILE_FIELDS = [
    {
        'name':       'status',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':      'Status',
            'help_text':  '',
            'max_length': 255,
            'widget':     '',
            'initial':    '',
            'required':   False,
        },
        'default':    '',
    },
    {
        'name':       'public',
        'group':      '',
        'xpath':      "",
        'xpath_dup':  [],
        'model_type': int,
        'form_type':  forms.IntegerField,
        'form': {
            'label':      'Public',
            'help_text':  '',
            'widget':     '',
            'initial':    0,
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
            'widget':     '',
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
