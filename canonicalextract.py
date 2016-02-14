"""
Handles processing of a downloaded web page
"""


import logging
from bs4 import BeautifulSoup, UnicodeDammit, FeatureNotFound
from canonicalencoding import try_encoding
from urlhelpers import url_or_error


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
    except Exception as ex:
        logging.exception(ex)

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
    except Exception as ex:
        logging.exception(ex)
        return None
    except Exception:
        pass

    # Try Canonical URL
    try:
        url_can = soup.find('link', rel='canonical')
        if url_can:
            url_new = url_can.get('href')
            if url_new:
                return url_or_error(url_new)
    except Exception:
        pass

    # Try Open Graph
    try:
        url_can = soup.find('meta', attrs={'property': 'og:url',
                                           'content': True})
        if url_can:
            u = url_can['content']
            if u:
                return url_or_error(u)

    except Exception:
        pass

    # logging.debug('no canonical url found')
    return None


def process_page(page, enc, url, ret_url, method):
    """Checks if page exists, if it can be decoded and if url can be extracted
    """
    # check if page was downloaded
    if page is None:
        # no content could be fetched
        return {'url_original': url,
                'url_retrieved': ret_url,
                'method': method,
                'reason': 'no content'}

    # check for decoding errors
    page = decode_web_page(page, enc)
    if page is None:
        # could not decode
        return {'url_original': url,
                'url_retrieved': ret_url,
                'method': method,
                'reason': 'decode failed'}

    # attempt to extract canonical/og url from content
    canonical = extract_canonical(page)
    if canonical is None:
        # couldnt extract canonical/og url
        return {'url_original': url,
                'url_retrieved': ret_url,
                'method': method,
                'reason': 'no attributes'}

    # we got it!!!
    ret_url = canonical
    method = 'canonical'

    return {'url_original': url,
            'url_retrieved': ret_url,
            'method': method,
            'reason': 'canonical'}
