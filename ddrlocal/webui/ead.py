from bs4 import BeautifulSoup

from django import forms


"""
<eadheader audience="internal" countryencoding="iso3166-1" 
dateencoding="iso8601" langencoding="iso639-2b" 
relatedencoding="DC" repositoryencoding="iso15511" 
scriptencoding="iso15924">
   <eadid countrycode="us" identifier="bachrach_lf" mainagencycode="NSyU">bachrach_lf</eadid>
   <filedesc>
      <titlestmt>
         <titleproper encodinganalog="Title">Louis Fabian Bachrach Papers</titleproper>
         <subtitle>An inventory of his papers at Blank University</subtitle>
         <author encodinganalog="Creator">Mary Smith</author>
      </titlestmt>
      <publicationstmt>
         <publisher encodinganalog="Publisher">Blank University</publisher>
         <date encodinganalog="Date" normal="1981">1981</date>
      </publicationstmt>
   </filedesc>
   <profiledesc>
      <creation>John Jones
         <date normal="2006-09-13">13 Sep 2006</date>
      </creation>
      <langusage>
         <language encodinganalog="Language" langcode="eng">English</language>
      </langusage>
   </profiledesc>
</eadheader>
"""

COUNTRY_CHOICES=[['us','US'],]
LANGUAGE_CHOICES=[['en','English'],
                  ['ja','Japanese'],
                  ['es','Spanish'],]

class EADHeaderForm(forms.Form):
    audience              = forms.CharField(max_length=255, required=True, initial='internal',)
    countryencoding       = forms.CharField(max_length=255, required=True, initial='iso3166-1',)
    dateencoding          = forms.CharField(max_length=255, required=True, initial='iso8601',)
    langencoding          = forms.CharField(max_length=255, required=True, initial='iso639-2b',) 
    relatedencoding       = forms.CharField(max_length=255, required=True, initial='DC',)
    repositoryencoding    = forms.CharField(max_length=255, required=True, initial='iso15511',)
    scriptencoding        = forms.CharField(max_length=255, required=True, initial='iso15924',)
    
    eadid                 = forms.CharField(max_length=255, required=True,)
    eadid_countrycode     = forms.ChoiceField(required=True, choices=COUNTRY_CHOICES,)
    eadid_identifier      = forms.CharField(max_length=255, required=True,)
    eadid_mainagencycode  = forms.CharField(max_length=255, required=True,)
    
    titlestmt_titleproper = forms.CharField(max_length=255, required=True,)
    titlestmt_subtitle    = forms.CharField(max_length=255, required=True,)
    titlestmt_author      = forms.CharField(max_length=255, required=True,)
    
    publicationstmt_publisher = forms.CharField(max_length=255, required=True,)
    publicationstmt_date  = forms.CharField(max_length=255, required=True,)
    
    profiledesc_creation  = forms.CharField(max_length=255, required=True,)
    profiledesc_date      = forms.DateField(required=True,)
    
    langcode              = forms.ChoiceField(required=True, choices=LANGUAGE_CHOICES,)


def prep_eadheader_form(xml):
    """Load data from existing EAD.xml into form.
    """
    data = {}
    soup = BeautifulSoup(xml, 'xml')
    soup = eadheader_expand(soup)
    
    data['audience']           = soup.ead.eadheader.get('audience', 'internal')
    data['countryencoding']    = soup.ead.eadheader.get('countryencoding', 'iso3166-1')
    data['dateencoding']       = soup.ead.eadheader.get('dateencoding', 'iso8601')
    data['langencoding']       = soup.ead.eadheader.get('langencoding', 'iso639-2b')
    data['relatedencoding']    = soup.ead.eadheader.get('relatedencoding', 'DC')
    data['repositoryencoding'] = soup.ead.eadheader.get('repositoryencoding', 'iso15511')
    data['scriptencoding']     = soup.ead.eadheader.get('scriptencoding', 'iso15924')

    data['eadid_countrycode']    = soup.ead.eadid.get('eadid_countrycode', 'us')
    data['eadid_identifier']     = soup.ead.eadid.get('eadid_identifier', None)
    data['eadid_mainagencycode'] = soup.ead.eadid.get('eadid_mainagencycode', None)
    data['eadid']                = soup.ead.eadid.string
    
    data['titlestmt_titleproper'] = soup.ead.eadheader.filedesc.titlestmt.titleproper.text
    data['titlestmt_subtitle']    = soup.ead.eadheader.filedesc.titlestmt.subtitle.text
    data['titlestmt_author']      = soup.ead.eadheader.filedesc.titlestmt.author.text
    
    data['publicationstmt_publisher'] = soup.ead.eadheader.filedesc.publicationstmt.publisher.string
    data['publicationstmt_date']      = soup.ead.eadheader.filedesc.publicationstmt.date.string
    
    data['profiledesc_creation'] = soup.ead.eadheader.profiledesc.creation.string
    data['profiledesc_date']     = soup.ead.eadheader.profiledesc.creation.date.get('normal', '')
     
    data['langcode'] = soup.ead.eadheader.profiledesc.langusage.language.get('langcode', '')

    for key,val in data.iteritems():
        if val:
            data[key] = val.strip()
    
    form = EADHeaderForm(data)
    return form

def eadheader_expand(soup):
    """Add tags if they're not already present.
    """
    if not soup.ead.eadheader:             soup.ead.append(soup.new_tag('eadheader'))
    if not soup.ead.eadheader.eadid:       soup.ead.eadheader.append(soup.new_tag('eadid'))
    if not soup.ead.eadheader.filedesc:    soup.ead.eadheader.append(soup.new_tag('filedesc'))
    if not soup.ead.eadheader.profiledesc: soup.ead.eadheader.append(soup.new_tag('profiledesc'))
    
    if not soup.ead.eadheader.filedesc.titlestmt:
        soup.ead.eadheader.filedesc.append(soup.new_tag('titlestmt'))
    if not soup.ead.eadheader.filedesc.titlestmt.titleproper:
        soup.ead.eadheader.filedesc.titlestmt.append(soup.new_tag('titleproper'))
    if not soup.ead.eadheader.filedesc.titlestmt.subtitle:
        soup.ead.eadheader.filedesc.titlestmt.append(soup.new_tag('subtitle'))
    if not soup.ead.eadheader.filedesc.titlestmt.author:
        soup.ead.eadheader.filedesc.titlestmt.append(soup.new_tag('author'))
    
    if not soup.ead.eadheader.filedesc.publicationstmt:
        soup.ead.eadheader.filedesc.append(soup.new_tag('publicationstmt'))
    if not soup.ead.eadheader.filedesc.publicationstmt.publisher:
        soup.ead.eadheader.filedesc.publicationstmt.append(soup.new_tag('publisher'))
    if not soup.ead.eadheader.filedesc.publicationstmt.date:
        soup.ead.eadheader.filedesc.publicationstmt.append(soup.new_tag('date'))
    
    if not soup.ead.eadheader.profiledesc.creation:
        soup.ead.eadheader.profiledesc.append(soup.new_tag('creation'))
    if not soup.ead.eadheader.profiledesc.creation.date:
        soup.ead.eadheader.profiledesc.creation.append(soup.new_tag('date'))
    if not soup.ead.eadheader.profiledesc.langusage:
        soup.ead.eadheader.profiledesc.append(soup.new_tag('langusage'))
    if not soup.ead.eadheader.profiledesc.langusage.langusage:
        soup.ead.eadheader.profiledesc.langusage.append(soup.new_tag('language'))
    
    return soup

def eadheader_xml(form, xml):
    """
    """
    soup = BeautifulSoup(xml, 'xml')
    soup = eadheader_expand(soup)
        
    soup.ead.eadheader['audience']           = form.cleaned_data.get('audience',           'internal')
    soup.ead.eadheader['countryencoding']    = form.cleaned_data.get('countryencoding',    'iso3166-1')
    soup.ead.eadheader['dateencoding']       = form.cleaned_data.get('dateencoding',       'iso8601')
    soup.ead.eadheader['langencoding']       = form.cleaned_data.get('langencoding',       'iso639-2b')
    soup.ead.eadheader['relatedencoding']    = form.cleaned_data.get('relatedencoding',    'DC')
    soup.ead.eadheader['repositoryencoding'] = form.cleaned_data.get('repositoryencoding', 'iso15511')
    soup.ead.eadheader['scriptencoding']     = form.cleaned_data.get('scriptencoding',     'iso15924')
    
    soup.ead.eadheader.eadid['eadid_countrycode'] = form.cleaned_data.get('eadid_countrycode','us')
    soup.ead.eadheader.eadid['eadid_identifier'] = form.cleaned_data.get('eadid_identifier','')
    soup.ead.eadheader.eadid['eadid_mainagencycode'] = form.cleaned_data.get('eadid_mainagencycode','')
    soup.ead.eadheader.eadid.string = form.cleaned_data.get('eadid','')

    soup.ead.eadheader.filedesc.titlestmt.titleproper['encodinganalog'] = 'Title'
    soup.ead.eadheader.filedesc.titlestmt.titleproper.string = form.cleaned_data.get('titlestmt_titleproper','')
    soup.ead.eadheader.filedesc.titlestmt.subtitle.string = form.cleaned_data.get('titlestmt_subtitle','')
    soup.ead.eadheader.filedesc.titlestmt.author['encodinganalog'] = 'Creator'
    soup.ead.eadheader.filedesc.titlestmt.author.string = form.cleaned_data.get('titlestmt_author','')
    
    soup.ead.eadheader.filedesc.publicationstmt.publisher['encodinganalog'] = 'Publisher'
    soup.ead.eadheader.filedesc.publicationstmt.publisher.string = form.cleaned_data.get('publicationstmt_publisher','')
    #soup.ead.eadheader.filedesc.publicationstmt.date['encodinganalog'] = 'Date'
    #soup.ead.eadheader.filedesc.publicationstmt.date['normal'] = form.cleaned_data.get('publicationstmt_date','')
    #soup.ead.eadheader.filedesc.publicationstmt.date.string = form.cleaned_data.get('publicationstmt_date','')
    
    #soup.ead.eadheader.profiledesc.creation.date['normal'] = form.cleaned_data.get('profiledesc_date','')
    #soup.ead.eadheader.profiledesc.creation.date.string = form.cleaned_data.get('profiledesc_date','')
    soup.ead.eadheader.profiledesc.creation.string = form.cleaned_data.get('profiledesc_creation','')
    
    soup.ead.eadheader.profiledesc.langusage.language['encodinganalog'] = 'Language'
    soup.ead.eadheader.profiledesc.langusage.language['langcode'] = form.cleaned_data.get('langcode','')
    soup.ead.eadheader.profiledesc.langusage.language.string = form.cleaned_data.get('langcode','')
    
    xml_new = soup.prettify()
    return xml_new
