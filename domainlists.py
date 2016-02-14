"""
Domain Whitelists
"""


import logging
import tldextract


def get_extractor(cache_file):
    """Creates a domain extractor with a specific cache
    """
    extract = tldextract.TLDExtract(cache_file=cache_file)
    return extract


def load_list(listpath):
    """Loads domain whitelist or shortener list
    """
    domain_list = set()

    with open(listpath) as fin:
        for line in fin:
            domain = line.decode('utf8').lower().strip()
            if domain:
                if not domain.startswith('#'):
                    domain_list.add(domain)

        msg = "Loaded whitelist list with {} domains".format(len(domain_list))
        logging.info(msg)
    return domain_list


def check_whitelist(url, method='missing method', extract=tldextract.extract,
                    whitelist=None):
    """If whitelist exists, check if url's domain is in it.
    """
    if whitelist:
        try:
            domain = extract(url).registered_domain.lower()
            # check if url is in whitelist
            if domain not in whitelist:
                domain = domain.encode('utf8')
                msg = "not in domain list:\t{} ({})".format(domain, method)
                logging.debug(msg)
                return False
        except Exception as ex:
            logging.warning(ex)
            return False

    return True
