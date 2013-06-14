from lxml import etree


def tagtype(tag):
    """some of these checks cause errors for some reason
    """
    try:
        if tag.is_text:
            return 'text'
    except:
        pass
    try:
        if tag.is_attribute:
            return 'attribute'
    except:
        pass
    try:
        if tag.is_tail:
            return 'tail'
    except:
        pass
    return 'unknown'

def gettag(tree, xpath, namespaces):
    """
    TODO Refactor this!!!
    For each field, only the first tag is retrieved, when there may be many that we are interested in.
    """
    tag = None
    tags = tree.xpath(xpath, namespaces=namespaces)
    if tags and len(tags):
        if (type(tags) == type([])):
            tag = tags[0]
        else:
            tag = tags
    return tag

def gettagvalue(tag):
    """Gets tag text, attribute, or tail, depending on the xpath

    NOTE: This seems to work with namespaced attributes, while settagvalue does not.
    """
    value = None
    if type(tag) == type(etree._ElementStringResult()):
        value = tag
    elif hasattr(tag, 'text'):
        value = tag.text
    elif type(tag) == type(''):
        value = tag
    elif tagtype(tag) == 'attribute':
        attr = f['xpath'].split('@')[1]
        value = tag.getparent().attrib[attr]
    # strip before/after whitespace
    try:
        value = value.strip()
    except:
        pass
    return value

def settagvalue(tag, xpath, value, namespaces):
    """Set the value of the tag/attribute.
    
    NOTE: Tag type 'attribute' has to work with both of these xpaths:
    - "/mets:mets/@OBJID"
    - "/mets:mets/mets:dmdSec[@ID='DM1']/mets:mdWrap/mets:xmlData/mods:mods/mods:subject/mods:topic/@xlink:href"
    
    TODO Is there an easier way to set a namespaced attribute in lxml???
    """
    if hasattr(tag, 'text'):
        tag.text = value
    elif type(tag) == type(''):
        tag = value
    elif tagtype(tag) == 'attribute':
        attr = xpath.rsplit('@',1)[-1]
        # namespaced attribute
        if attr.find(':') > -1:
            attr = expand_attrib_namespace(attr, namespaces)
        tag.getparent().attrib[attr] = value
    return tag

def expand_attrib_namespace(attr, namespaces):
    """
    """
    ns,a = attr.split(':')
    return '{%s}%s' % (namespaces[ns], a)
