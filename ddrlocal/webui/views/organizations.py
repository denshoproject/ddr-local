from pathlib import Path

from django.conf import settings
from django.shortcuts import Http404, render

from storage.decorators import storage_required
from webui import gitolite
from webui.models import Organization


@storage_required
def list(request):
    gitolite_orgs = gitolite.get_repos_orgs()
    organizations = Organization.organizations(settings.MEDIA_BASE)
    for org in organizations:
        org['img'] = f"{settings.MEDIA_URL}ddr/{org['id']}/logo.png"

    return render(request, 'webui/organizations/list.html', {
        'organizations': organizations,
    })

@storage_required
def detail(request, oid):
    org_path = Path(settings.MEDIA_BASE) / oid
    organization = Organization.get(oid, settings.MEDIA_BASE)
    organization['img'] = f"{settings.MEDIA_URL}ddr/{oid}/logo.png"
    collections = Organization.children(org_path)
    return render(request, 'webui/organizations/detail.html', {
        'organization': organization,
        'collections': collections,
    })
