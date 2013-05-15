import datetime
import StringIO

from lxml import etree

from django import forms

from xmlforms.forms import XMLForm


METS_XML = """<mets>
  <metsHdr createdate="" lastmoddate="">
    <agent>
      <name/>
    </agent>
  </metsHdr>
  <dmdSec></dmdSec>
  <amdSec></amdSec>
  <fileSec></fileSec>
  <structMap></structMap>
  <structLink></structLink>
  <behaviorSec></behaviorSec>
</mets>"""

METSHDR_FIELDS = [
    {
        'name':       'metshdr_createdate',
        'xpath':      '/mets/metsHdr/@createdate',
        'model_type': datetime.datetime,
        'form_type':  forms.DateTimeField,
        'form': {
            'label':     'Create Date',
            'help_text': 'YYYY-MM-DD HH:MM:SS',
            'widget':    '',
            'initial':   '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'metshdr_lastmoddate',
        'xpath':      '/mets/metsHdr/@lastmoddate',
        'model_type': datetime.datetime,
        'form_type':  forms.DateTimeField,
        'form': {
            'label':     'Last Mod Date',
            'help_text': 'YYYY-MM-DD HH:MM:SS',
            'widget':    '',
            'initial':   '',
            'required': True,
        },
        'default':    '',
    },
    {
        'name':       'metshdr_agent',
        'xpath':      '/mets/metsHdr/agent/name',
        'model_type': str,
        'form_type':  forms.CharField,
        'form': {
            'label':     'Agent Name',
            'help_text': '',
            'widget':    '',
            'initial':   '',
            'max_length': 255,
            'required': True,
        },
        'default':    '',
    },
]


class MetshdrForm(XMLForm):
    
    def __init__(self, *args, **kwargs):
        super(MetshdrForm, self).__init__(*args, **kwargs)
    
    @staticmethod
    def process(xml, fields, form):
        """<metshdr>-specific processing
        """
        xml = XMLForm.process(xml, fields, form)
        tree = etree.parse(StringIO.StringIO(xml))
        for f in fields:
            pass
        return etree.tostring(tree, pretty_print=True)
