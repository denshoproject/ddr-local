from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)

from django.http import HttpResponse
from django.template import Template

from webui import supervisord


STATE_BOOTSTRAP_ALERTS = {
    'STARTING': 'warning',
    'RUNNING': 'success',
    'BACKOFF': 'warning',
    'STOPPING': 'danger',
    'STOPPED': 'danger',
    'EXITED': 'danger',
    'FATAL': 'danger',
    'UNKNOWN': 'danger',
}
PROCINFO_TEMPLATE = """
<div id="ddrlocal" class="alert alert-{{ ddrlocal.alert_class }}">
    {{ ddrlocal.timestamp }}: ddrlocal &mdash; {{ ddrlocal.statename }}
    {% if ddrlocal.description %} &mdash; {{ ddrlocal.description }}{% endif %}
</div>
<div id="celery" class="alert alert-{{ celery.alert_class }}">
    {{ celery.timestamp }}: celery &mdash; {{ celery.statename }}
    {% if celery.description %} &mdash; {{ celery.description }}{% endif %}
</div>
<div id="celerybeat" class="alert alert-{{ celerybeat.alert_class }}">
    {{ celerybeat.timestamp }}: celerybeat &mdash; {{ celerybeat.statename }}
    {% if celerybeat.description %} &mdash; {{ celerybeat.description }}{% endif %}
</div>
"""

def procinfo_html( request ):
    """Supervisord procinfo for ddr-local apps as a Bootstrap <alert> tag.
    """
    data = supervisord.process_info()
    # add some data used in template
    for name in data['procs']:
        data[name]['alert_class'] = STATE_BOOTSTRAP_ALERTS[data[name]['statename']]
        data[name]['timestamp'] = datetime.fromtimestamp(data[name]['now'])
    t = Template(PROCINFO_TEMPLATE)
    html = t.render(data)
    return HttpResponse(html)

def procinfo_json( request ):
    """Supervisord procinfo for ddr-local apps as JSON.
    """
    data = supervisord.process_info()
    return HttpResponse(json.dumps(data), content_type="application/json")

def restart( request ):
    """Request a restart of supervisord.
    """
    restarted = supervisord.restart()
    return HttpResponse(json.dumps({'restarted':restarted}), content_type="application/json")
