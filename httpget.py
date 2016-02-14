"""
HTTP Request for a web page
"""


import logging
import requests
from urlhelpers import url_or_error
from tornado.httpclient import AsyncHTTPClient


def get_web_page(url, timeout):
    ''' Fetches content at a given URL.
    Requests implementation.
    Args:
        url - unicode string

    Returns: (data, enc, final_url, None)
              or
             (None, None, None, Reason) on error.
    '''

    url = url_or_error(url)
    if url is None:
        return (None, None, None, 'url')

    reason = 'unk'  # default error resason

    # Download and Processs
    try:
        req = requests.get(url, timeout=timeout, allow_redirects=True,
                           stream=True)
        req.raise_for_status()

        # Get Response URL
        final_url = req.url

        # Get Encoding
        enc = req.encoding

        # Get content-type
        content_type = req.headers.get('content-type')

        if content_type and 'text/html' not in content_type:
            msg = 'content type not supported %s for %s' % (content_type, url)
            logging.debug(msg)
            return (None, enc, final_url, 'content-type')

        # get data
        data = req.content

        return (data, enc, final_url, None)

    except requests.exceptions.Timeout:
        msg = 'timedout: {}'.format(url)
        logging.debug(msg)
        reason = 'timeout'

    except requests.exceptions.HTTPError:
        msg = 'download failed: url=%s reason: %d' % (url, req.status_code)
        logging.debug(msg)
        reason = str(req.status_code)

    except Exception as ex:
        msg = 'download failed: url=%s with %s' % (url, repr(ex))
        logging.debug(msg)
        reason = 'download'

    return (None, None, None, reason)


def make_request_handler(processed_handler):
    """
    Makes a response handler from a processed_handler
    """
    def handle_request(response):
        url = response.request.url

        if response.error:
            reason = str(response.error)
            logging.debug(reason)
            result = (url, None, None, None, reason)
        elif 'Content-Type' not in response.headers:
            reason = 'no content-type for {}'.format(url)
            logging.debug(reason)
            result = (url, None, None, None, reason)
        elif 'text/html' not in response.headers['Content-Type']:
            reason = 'content type not supported {} for {}'
            reason = reason.format(response.headers['Content-Type'], url)
            logging.debug(reason)
            result = (url, None, None, response.effective_url, reason)

        else:  # unqualified success as far as this function is concerned
            result = (url, response.body, 'utf8', response.effective_url, None)

        # logging.debug('req_handler -> sending -> process_handler')
        processed_handler(result)

    return handle_request


def get_web_page_async(url, timeout, maxsize, maxclients, processed_handler):
    ''' Fetches content at a given URL.
    Requests implementation.
    Args:
        url - unicode string

    Returns: (data, enc, final_url, None)
              or
             (None, None, None, Reason) on error.
    '''

    url = url_or_error(url)
    if url is None:
        processed_handler((None, None, None, 'url'))

    http_client = AsyncHTTPClient(max_clients=maxclients,
                                  max_buffer_size=maxsize)
    # Download and Processs
    handle_request = make_request_handler(processed_handler)
    http_client.fetch(url, handle_request)
