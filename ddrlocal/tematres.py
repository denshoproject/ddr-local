"""Interact with a TemaTres vocabulary server.
"""


def get_terms(urls):
    """Get the string referred to by a Tematres JSON URL.
    
    TODO Would an async lib like grequests or requests-futures go faster?
    @param urls: List of urls
    @returns list of (url,term) tuples
    """
    import requests
    terms = []
    for url in urls:
        r = requests.get(url)
        if (r.status_code == 200) and r.text:
            json = r.json()
            terms.append( (url, json['string']))
    #import grequests
    #rs = (grequests.get(u) for u in urls)
    #responses = grequests.map(rs, size=2)
    #for r in responses:
    #    if r.status_code == 200:
    #        json = r.json()
    #        terms.append( (url, json['string']))
    return terms
