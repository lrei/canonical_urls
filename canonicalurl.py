'''
(C) 2015
Author: Luis Rei <luis.rei@ijs.si>
Author: Gregor Leban <gregor.leban@ijs.si>
License: MIT License
Fetches canonical (or open graph) version of URL
Failing that, returns redirect url if redirect happens.

'''

from __future__ import print_function
# Others
import logging
import urllib2
import re
import gzip
from StringIO import StringIO
from cookielib import CookieJar
from bs4 import BeautifulSoup, UnicodeDammit
import urlparse
import rfc3987

logging.getLogger("bs4").setLevel(logging.ERROR)


REQ_TIMEOUT = 30
MAX_READ = 2 * 1024 * 1024  # 2MB - Probably Enough for The Verge's HTML


class MyHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    ''' Redirect Handler '''
    # pylint: disable=no-init
    def http_error_302(self, req, fp, code, msg, headers):
        return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code,
                                                          msg, headers)


def url_encode_non_ascii(b):
    return re.sub('[\x80-\xFF]', lambda c: '%%%02x' % ord(c.group(0)), b)


def ensure_url(iri):
    '''If IRI, convert to URL
    If fragments (#), remove
    http://stackoverflow.com/posts/4391299/revisions
    '''
    parts = urlparse.urlparse(iri)
    url_parts = []

    for index, part in enumerate(parts):
        if index == 1:
            url_parts.append(part.lower().encode('idna'))
        else:
            url_parts.append(url_encode_non_ascii(part.encode('utf-8')))

    url = urlparse.urlunparse(url_parts)
    url = urlparse.urldefrag(url)[0]

    return url


def validate_url(url):
    '''
    Validates URL (actually, IRIs).
    '''
    try:
        rfc3987.parse(url, rule='IRI')
    except:
        return False

    return True


def read_gzip(response):
    buf = StringIO(response.read(MAX_READ))
    f = gzip.GzipFile(fileobj=buf)
    data = f.read()
    return data


def read_deflate(response):
    buf = StringIO(response.read(MAX_READ))
    f = zlib.decompress(buf)
    data = f.read()
    return data


def get_web_page(url):
    ''' Fetches content at a given URL.
    Args:
        url - unicode string

    Returns: (html, headers, final_url) or (None, None, None) on error.
    '''

    # if it's not unicode, it must be utf8, otherwise fail
    if not isinstance(url, unicode):
        try:
            s = url.decode('utf8')
        except Exception as e:
            logging.exception(e)
            return (url, None, None)


    # Convert URI to URL if necessary
    try:
        url = ensure_url(url)
    except Exception as e:
        logging.exception(e)
        return (url, None, None)

    # Validate URL
    if not validate_url(url):
        logging.info('bad url: %s ' % url)
        return (url, None, None)

    # 
    # Download and Processs
    #
    try:
        # open page using cookie support and url redirects
        cookie_jar = CookieJar()
        opener = urllib2.build_opener(MyHTTPRedirectHandler,
                                      urllib2.HTTPCookieProcessor(cookie_jar))
        headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:10.0.1) Gecko/20100101 Firefox/10.0.1',
        }
        opener.addheaders = headers.items()
        response = opener.open(url, None, REQ_TIMEOUT)
        content_encoding = response.info().get('Content-Encoding') 
        html = None
        if content_encoding is not None:
            if  content_encoding in ('gzip', 'x-gzip'):
                html = read_gzip(response)
            elif content_encoding == 'deflate':
                html = read_deflate(response)
            else:
                html = response.read(MAX_READ)
        else:
                html = response.read(MAX_READ)

        final_url = response.geturl()
        return (html, response.headers, final_url)

    except urllib2.HTTPError as ex:
        msg = 'download failed: url=%s http error code: %d' % (url, ex.code)
        logging.debug(msg)
        return (None, None, None)

    except Exception as ex:
        msg = 'download failed: url=%s' % (url,)
        logging.debug(msg)
        return (None, None, None)

    return (None, None, None)


def decode_web_page(html, headers):
    '''
    Returns unicode str containing the HTML content of the web page
    '''
    try:
        # try first using the encoding that was provided by the publisher
        encoding = headers['content-type'].split('charset=')[-1]
        ucontent = unicode(html, encoding, 'replace')
        return ucontent
    # if we fail, resort to UnicodeDammit
    except Exception:
        try:
            ucontent = UnicodeDammit(html, is_html=True)
            return ucontent
        except Exception:
            return None


def extract_canonical(unicode_content):
    '''Extracts canonical URL or Open Graph URL from the content'''
    try:
        soup = BeautifulSoup(unicode_content, 'html5lib')
    except:
        return None

    # Try Canonical URL
    try:
        url_can = soup.find('link', rel='canonical')
        if url_can:
            u = url_can['content']
            u = ensure_url(u)
            if validate_url(u):
                return u

    except Exception:
        pass

    # Try Open Graph
    try:
        url_can = soup.find('meta', attrs={'property': 'og:url',
                                           'content': True})
        if url_can:
            u = url_can['content']
            u = ensure_url(u)
            if validate_url(u):
                return u

    except Exception:
        pass

    # Failed
    return None


def get_canonical_url(url):
    '''Get the canonical (or open graph) URL
    Returns a triple (original_url, new_url, method)

    where method in ['canonical', 'redirect', 'original']
    '''
    method = 'original'
    ret_url = url

    # if it's not unicode, it must be utf8, otherwise fail
    if not isinstance(url, unicode):
        try:
            url = url.decode('utf8')
        except Exception as e:
            logging.exception(e)
            return (url, None, None)

    page, headers, final_url = get_web_page(url)
    if final_url is not None:
        if not isinstance(final_url, unicode):
            final_url = final_url.decode('utf8')
        if final_url != url:
            ret_url = ensure_url(final_url)
            method = 'redirect'

    # check if page was downloaded
    if page is None:
        # no content could be fetched
        return (url, ret_url, method)

    # check for decoding errors
    page = decode_web_page(page, headers)
    if page is None:
        # could not decode
        return (url, ret_url, method)

    # attempt to extract canonical/og url from content
    canonical = extract_canonical(page)
    if canonical is None:
        # couldnt extract canonical/og url
        return (url, ret_url, method)

    # we got it!!!
    ret_url = canonical
    method = 'canonical'

    return (url, ret_url, method)
