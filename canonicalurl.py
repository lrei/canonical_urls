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
from httpget import get_web_page, get_web_page_async
from urlhelpers import url_or_error
from domainlists import check_whitelist
from canonicalextract import process_page


REQ_TIMEOUT = 30
MAX_READ = 2 * 1024 * 1024  # 2MB


def get_canonical_url(url, whitelist, expandlist, extract,
                      timeout=REQ_TIMEOUT):
    '''Get the canonical (or open graph) URL
    Returns a 4-tuple (original_url, new_url, method, reason)

    where method in ['canonical', 'redirect', 'original']
    '''
    method = 'original'
    ret_url = url

    # if it's not unicode, it must be utf8, otherwise fail
    url_new = url_or_error(url)
    if url_new is None:
        return {'url_original': url,
                'url_retrieved': None,
                'method': method,
                'reason': 'invalid url'}
    url = url_new

    # Only download URLs that are in the WHITELIST  or in the EXPANDLIST
    if not (check_whitelist(url, method, extract, expandlist) or
            check_whitelist(url, method, extract, whitelist)):
        return {'url_original': url,
                'url_retrieved': ret_url,
                'method': method,
                'reason': 'not in lists'}

    #
    # fetch page
    #
    page, enc, final_url, err = get_web_page(url, timeout)

    # check final url from dowload attempt
    if final_url is not None:
        if not isinstance(final_url, unicode):
            final_url = final_url.decode('utf8')

        if final_url != url:
            ret_url = url_or_error(final_url)
            if ret_url is not None:
                method = 'redirect'
                logging.debug('got redirect')
            else:
                method = 'bad url'
        else:
            ret_url = final_url

    # check if whitelist exists
    if (ret_url is None or
            not check_whitelist(ret_url, method, extract, whitelist)):
        return {'url_original': url,
                'url_retrieved': ret_url,
                'method': method,
                'reason': 'not in whitelist'}

    return process_page(page, enc, url, ret_url, method)


def make_processed_handler(canonical_handler, whitelist, extract):
    """Returns a handler take processes the downloaded web page
    """
    def processed_handler(data):
        url, page, enc, final_url, err = data
        ret_url = None
        method = 'original'
        # check final url from dowload attempt
        if final_url is None:
            result = {'url_original': url,
                      'url_retrieved': None,
                      'method': None,
                      'reason': 'unreachable'}
            canonical_handler(result)
            return

        if final_url != url:
            ret_url = url_or_error(final_url)
            method = 'redirect'
            msg = 'got redirect: {} -> {}'.format(url, final_url)
            logging.debug(msg)
        else:
            ret_url = url

        # check if whitelist exists
        if not check_whitelist(ret_url, method, extract, whitelist):
            result = {'url_original': url,
                      'url_retrieved': ret_url,
                      'method': None,
                      'reason': 'not in whitelist'}
            canonical_handler(result)
            return

        result = process_page(page, enc, url, ret_url, method)
        canonical_handler(result)

    return processed_handler


def get_canonical_url_async(url, whitelist, expandlist, extract,
                            timeout, maxsize, maxclients, canonical_handler):
    '''Get the canonical (or open graph) URL
    Returns a 4-tuple (original_url, new_url, method, reason)

    where method in ['canonical', 'redirect', 'original']
    '''
    method = 'original'
    ret_url = url

    # if it's not unicode, it must be utf8, otherwise fail
    url_new = url_or_error(url)
    if url_new is None:
        result = {'url_original': url,
                  'url_retrieved': None,
                  'method': method,
                  'reason': 'invalid url'}
        canonical_handler(result)
        return

    url = url_new
    # Only download URLs that are in the WHITELIST  or in the EXPANDLIST
    if not (check_whitelist(url, method, extract, expandlist) or
            check_whitelist(url, method, extract, whitelist)):
        result = {'url_original': url,
                  'url_retrieved': ret_url,
                  'method': method,
                  'reason': 'not in lists'}
        logging.debug('passing result 1')
        canonical_handler(result)
        return

    # fetch page
    processed_handler = make_processed_handler(canonical_handler, whitelist,
                                               extract)
    get_web_page_async(url, timeout, maxsize, maxclients, processed_handler)
