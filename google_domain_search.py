#!/usr/bin/env python
__all__ = [

    # Main search function.
    'search',

    # Miscellaneous utility functions.
    'get_random_user_agent',
]

import os
import random
import sys
import time
import math

if sys.version_info[0] > 2:
    from urllib.request import Request, urlopen
    from urllib.parse import quote_plus, urlparse, parse_qs
else:
    from urllib import quote_plus
    from urllib2 import Request, urlopen
    from urlparse import urlparse, parse_qs

try:
    from bs4 import BeautifulSoup
    is_bs4 = True
except ImportError:
    from BeautifulSoup import BeautifulSoup
    is_bs4 = False

# URL templates to make Google searches.
url_home = "https://www.google.%(tld)s/"
url_search = "https://www.google.%(tld)s/search?hl=%(lang)s&q=%(query)s&" \
             "btnG=Google+Search&tbs=%(tbs)s&safe=%(safe)s&tbm=%(tpe)s"
url_next_page = "https://www.google.%(tld)s/search?hl=%(lang)s&q=%(query)s&" \
                "start=%(start)d&tbs=%(tbs)s&safe=%(safe)s&tbm=%(tpe)s"
url_search_num = "https://www.google.%(tld)s/search?hl=%(lang)s&q=%(query)s&" \
                 "num=%(num)d&btnG=Google+Search&tbs=%(tbs)s&safe=%(safe)s&" \
                 "tbm=%(tpe)s"
url_next_page_num = "https://www.google.%(tld)s/search?hl=%(lang)s&" \
                    "q=%(query)s&num=%(num)d&start=%(start)d&tbs=%(tbs)s&" \
                    "safe=%(safe)s&tbm=%(tpe)s"


# Default user agent, unless instructed by the user to change it.
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko)'

# Get a random user agent.
def get_random_user_agent():
    """
    Get a random user agent string.

    """
    return random.choice(user_agents_list)


# Request the given URL and return the response page, using the cookie jar.
def get_page(url):
    request = Request(url)
    request.add_header('User-Agent', USER_AGENT)
    response = urlopen(request)
    html = response.read()
    response.close()
    return html

def filter_customized_result(link, domains):
    try:
        o = urlparse(link, 'http')
        if o.netloc and o.netloc in domains:
            return link

        # Decode hidden URLs.
        if link.startswith('/url?'):
            link = parse_qs(o.query)['q'][0]

            o = urlparse(link, 'http')

            if o.netloc and o.netloc in domains:
                return link

    # Otherwise, or on error, return None.
    except Exception:
        pass
    return None


# Returns a generator that yields URLs.
def search_with_customized(query, tld='com', lang='en', tbs='0', safe='off', num=10, start=0,
           stop=None, domains=None, pause=2.0, only_standard=False,
           extra_params={}, tpe='', user_agent=None):
 
    hashes = set()

    # Prepare domain list if it exists.
    if domains:
        domain_query = '+OR+'.join('site:' + domain for domain in domains)
    else:
        domain_query = ''

    # Prepare the search string.
    query = quote_plus(query + '+' + domain_query)
    # Check extra_params for overlapping
    for builtin_param in ('hl', 'q', 'btnG', 'tbs', 'safe', 'tbm'):
        if builtin_param in extra_params.keys():
            raise ValueError(
                'GET parameter "%s" is overlapping with \
                the built-in GET parameter',
                builtin_param
            )

    # Prepare the URL of the first request.
    if start:
        if num == 10:
            url = url_next_page % vars()
        else:
            url = url_next_page_num % vars()
    else:
        if num == 10:
            url = url_search % vars()
        else:
            url = url_search_num % vars()
    # Loop until we reach the maximum result, if any (otherwise, loop forever).
    while not stop or start < stop:

        try:  # Is it python<3?
            iter_extra_params = extra_params.iteritems()
        except AttributeError:  # Or python>3?
            iter_extra_params = extra_params.items()

        # Append extra GET_parameters to URL
        for k, v in iter_extra_params:
            url += url + ('&%s=%s' % (k, v))

        # Sleep between requests.
        time.sleep(pause)

        # Request the Google Search results page.
        url = url.replace('%2Bsite', '+site')
        html = get_page(url)

        # Parse the response and process every anchored URL.
        if is_bs4:
            soup = BeautifulSoup(html, 'html.parser')
        else:
            soup = BeautifulSoup(html)
        anchors = soup.find(id='search').findAll('a')

        for a in anchors:

            # Leave only the "standard" results if requested.
            # Otherwise grab all possible links.
            if only_standard and (
                    not a.parent or a.parent.name.lower() != "h3"):
                continue
            # Get the URL from the anchor tag.
            try:
                link = a['href']
            except KeyError:
                continue

            # Filter invalid links and links pointing to Google itself.
            link = filter_customized_result(link, domains)

            if not link:
                continue
            # Discard repeated results.

            h = hash(link)
            if h in hashes:
                continue
            hashes.add(h)

            # Yield the result.
            yield link

        # End if there are no more results.
        if not soup.find(id='nav'):
            break

        # Prepare the URL for the next request.
        start += num
        if num == 10:
            url = url_next_page % vars()
        else:
            url = url_next_page_num % vars()
