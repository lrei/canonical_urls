"""
"""

import re
import logging
import rfc3987
import urlparse


def url_encode_non_ascii(b):
    return re.sub('[\x80-\xFF]', lambda c: '%%%02x' % ord(c.group(0)), b)


def ensure_url(iri):
    '''If IRI, convert to URL
    If fragments (#), remove
    http://stackoverflow.com/posts/4391299/revisions
    '''
    # if it's not unicode, it must be utf8, otherwise fail
    if not isinstance(iri, unicode):
        try:
            uri = iri.decode('utf8')  # noqa - we check if decoding works here
        except Exception as e:
            logging.exception(e)
            return None

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


def url_or_error(url):
    """Return a valid url or None
    """
    # if it's not unicode, it must be utf8, otherwise fail
    if not isinstance(url, unicode):
        try:
            url = url.decode('utf8')  # noqa - we check if decoding works here
        except Exception as e:
            logging.exception(e)
            return None

    # Convert URI to URL if necessary
    try:
        url = ensure_url(url)
    except Exception as e:
        logging.exception(e)
        return None

    # Validate URL
    if not validate_url(url):
        msg = 'bad url: {} '.format(url)
        logging.error(msg)
        return None

    return url
