'''
(C) 2015
Author: Luis Rei <luis.rei@ijs.si>
Author: Gregor Leban <gregor.leban@ijs.si>
License: MIT License
Fetches canonical (or open graph) version of URL
Failing that, returns redirect url if redirect happens.

'''

from __future__ import print_function
import logging
import re
import requests
from bs4 import BeautifulSoup, UnicodeDammit, FeatureNotFound
import urlparse
import rfc3987
from canonicalencoding import get_declared_encodings 
from canonicalencoding import detect_encoding, try_encoding, try_encoding_force



REQ_TIMEOUT = 30
MAX_READ = 2 * 1024 * 1024  # 2MB - Probably Enough for The Verge's HTML


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
        r = requests.get(url, timeout=REQ_TIMEOUT, allow_redirects=True,
                         stream=True)
        r.raise_for_status()

        # Get Response URL
        final_url = r.url

        # Get Encoding
        enc = r.encoding

        # Get content-type
        content_type = r.headers.get('content-type')

        if content_type and 'text/html' not in content_type:
            msg = 'content type not supported %s for %s' % (content_type, url)
            logging.debug(msg)
            return (None, enc, final_url)

        # get data
        data = r.content

        return (data, enc, final_url)

    except requests.exceptions.HTTPError as e:
        msg = 'download failed: url=%s reason: %d' % (url, r.status_code)
        logging.debug(msg)
        return (None, None, None)

    except Exception as ex:
        msg = 'download failed: url=%s with %s' % (url, repr(ex))
        logging.debug(msg)
        return (None, None, None)

    return (None, None, None)


def decode_web_page(html, enc):
    '''
    Returns unicode str containing the HTML content of the web page
    '''

    # Guard against Empty
    if html is None:
        logging.debug('no content')
        return None

    encodings = []
    
    # try first using the encoding that was provided by the headers
    if enc is not None:
        ucontent = try_encoding(html, enc)
        if ucontent is not None:
            return ucontent
        logging.debug('header encoding failed')

        encodings.append(enc)

    # if we fail, resort to UnicodeDammit
    # because we have cchardet installed, this will try to use it
    try:
        ucontent = UnicodeDammit(html, is_html=True).unicode_markup

        return ucontent
    except Exception:
        pass

    # honestly, how did we get here?
    logging.debug('UnicodeDammit failed')

    return None


def extract_canonical(unicode_content):
    '''Extracts canonical URL or Open Graph URL from the content'''
    try:
        soup = BeautifulSoup(unicode_content, 'html5lib')
    except FeatureNotFound:
        logging.exception('missing html5lib?')
        raise
    except Exception as e:
        logging.exception(e)
        return None

    # Try Canonical URL
    try:
        url_can = soup.find('link', rel='canonical')
        if url_can:
            u = url_can.get('href')
            logging.debug('got canonical')
            if u:
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
            if u:
                logging.debug('got open graph')
                u = ensure_url(u)
                if validate_url(u):
                    return u

    except Exception:
        pass

    # Failed
    logging.debug('no canonical url found')

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
            return (url, None, None, 'invalid url')

    page, headers, final_url = get_web_page(url)
    if final_url is not None:
        if not isinstance(final_url, unicode):
            final_url = final_url.decode('utf8')
        if final_url != url:
            ret_url = ensure_url(final_url)
            method = 'redirect'
            logging.debug('got redirect')


    # check if page was downloaded
    if page is None:
        # no content could be fetched
        return (url, ret_url, method, 'no content')

    # check for decoding errors
    page = decode_web_page(page, headers)
    if page is None:
        # could not decode
        return (url, ret_url, method, 'decode failed')

    # attempt to extract canonical/og url from content
    canonical = extract_canonical(page)
    if canonical is None:
        # couldnt extract canonical/og url
        return (url, ret_url, method, 'no attributes')

    # we got it!!!
    ret_url = canonical
    method = 'canonical'

    return (url, ret_url, method, 'canonical')
