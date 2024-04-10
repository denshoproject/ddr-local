from pathlib import Path

from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import Http404, render

from storage.decorators import storage_required
from webui import gitolite
from webui.models import Organization


@storage_required
def list(request):
    gitolite_orgs = gitolite.get_repos_orgs()
    organizations = Organization.organizations(settings.MEDIA_BASE)
    # densho must come first
    index = [n for n,o in enumerate(organizations) if o['id'] == 'ddr-densho'][0]
    densho = organizations.pop(index)
    organizations.insert(0, densho)
    # image link
    for org in organizations:
        org['img'] = f"{settings.MEDIA_URL}ddr/{org['id']}/logo.png"
    # make densho first
    return render(request, 'webui/organizations/list.html', {
        'organizations': organizations,
        'num_organizations': len(organizations),
    })

@storage_required
def detail(request, oid):
    org_path = Path(settings.MEDIA_BASE) / oid
    organization = Organization.get(oid, settings.MEDIA_BASE)
    organization['img'] = f"{settings.MEDIA_URL}ddr/{oid}/logo.png"
    # collections
    objects = Organization.children(org_path)
    thispage = request.GET.get('page', 1)
    paginator = Paginator(objects, settings.RESULTS_PER_PAGE)
    page = paginator.page(thispage)
    return render(request, 'webui/organizations/detail.html', {
        'organization': organization,
        'num_collections': len(objects),
        'paginator': paginator,
        'page': page,
        'thispage': thispage,
    })
