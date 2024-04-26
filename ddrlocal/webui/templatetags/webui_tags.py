from collections import OrderedDict

from django import template
from django.conf import settings

from webui.models import MODEL_PLURALS

register = template.Library()

def collection( obj ):
    """list-view collection template
    """
    t = template.loader.get_template('webui/collections/list-object.html')
    return t.render({'object':obj})

def entity( obj ):
    """list-view entity template
    """
    t = template.loader.get_template('webui/entities/list-object.html')
    return t.render({'object':obj})

def file( obj ):
    """list-view file template
    """
    t = template.loader.get_template('webui/files/list-object.html')
    return t.render({'object':obj})

def breadcrumbs(obj, endpoint=''):
    identifier = obj.identifier
    breadcrumbs = identifier.breadcrumbs(endpoint)
    t = template.loader.get_template('webui/breadcrumbs.html')
    return t.render({'breadcrumbs': breadcrumbs})

@register.filter(name='formaticon')
def formaticon( code ):
    """returns fa icon for the given entity.format code
    """
    icon = 'fa-file-text-o'
    if code == 'img':
        icon = 'fa-file-image-o'
    elif code == 'vh' or code == 'av':
        icon = 'fa-film'
    return icon

GALLERYITEM_DIV = """<div class="media " style="border:2px dashed red;">{}</div>"""

def galleryitem( obj ):
    """gallery-view item template
    """
    try:
        model_plural = MODEL_PLURALS[obj['model']]
    except:
        return GALLERYITEM_DIV.format(str(obj))
    template_path = 'webui/%s/gallery-object.html' % model_plural
    t = template.loader.get_template(template_path)
    return t.render({'object':obj})

LISTITEM_DIV = """<div class="media " style="border:2px dashed red;">{}</div>"""

def listitem( obj ):
    """list-view item template
    """
    try:
        model_plural = MODEL_PLURALS[obj['model']]
    except:
        return LISTITEM_DIV.format(str(obj))
    template_path = 'webui/%s/list-object.html' % model_plural
    t = template.loader.get_template(template_path)
    return t.render({'object':obj})

OBJECT_HEADER_TEMPLATE = """
<div class="media" style="padding-bottom:10px;">
  <div class="pull-left">
    <a href="{% url "webui-detail" organization_id %}">
      <img src="{{ img }}" class="img-responsive" style="width:100px;"/>
    </a>
  </div>
  <div class="media-body">
    <h1>
      {{ obj.id }} {% if obj.title %}&mdash; {{ obj.title }}{% endif %}
    </h1>
  </div>
</div>
"""

def object_header(obj):
    """Returns <h1> header with object.title and organization logo"""
    if isinstance(obj,dict) or isinstance(obj,OrderedDict) and obj.get('identifier'):
        organization_id = obj['id']
    elif getattr(obj,'identifier'):
        organization_id = obj.identifier.organization_id()
    else:
        raise(
            'ERROR: webui.templatetags.webui_tags.object_header only works ' \
            'with objects that have an Identifier'
        )
    img = f"{settings.MEDIA_URL}ddr/{organization_id}/logo.png"
    t = template.Template(OBJECT_HEADER_TEMPLATE)
    c = template.Context({
        'obj': obj,
        'organization_id':organization_id,
        'img':img,
    })
    html = t.render(c)
    return html

register.simple_tag(collection)
register.simple_tag(entity)
register.simple_tag(file)
register.simple_tag(breadcrumbs)
register.simple_tag(galleryitem)
register.simple_tag(listitem)
register.simple_tag(object_header)
