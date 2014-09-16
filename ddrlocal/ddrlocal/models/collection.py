# FIELDS = [
#     {
#         'name':       '',       # The field name.
#         'model_type': str,      # Python data type for the field.
#         'default':    '',       # Default value.
#         'inheritable': '',      # Whether or not the field is inheritable.
#         
#         'form_type':  '',       # Name of Django forms.Field object.
#         'form': {               # Kwargs to be passed to the forms.Field object.
#                                 # See Django forms documentation.
#             'label':     '',    # Pretty, human-readable name of the field.
#                                 # Note: label is also used in the UI outside of forms.
#             'help_text': '',    # Help for hapless users.
#             'widget':    '',    # Name of Django forms.Widget object.
#             'initial':   '',    # Initial value of field in a form.
#         },
#         
#         'xpath':      "",       # XPath to where field value resides in EAD/METS.
#         'xpath_dup':  [],       # Secondary XPath(s). We really should just have one xpath list.
#     },
# ]
FIELDS = []

UNDEFINED = True
