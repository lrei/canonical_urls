"""
Provides filtering of domains according to a list
"""

import inspect
import os
import logging
import tldextract

# General logging
logging.basicConfig(level=logging.INFO)

# module logger
logger = logging.getLogger("urlfixer")
logger.setLevel(logging.DEBUG)
ch = logging.FileHandler("/tmp/urlfix.log", encoding='utf8')
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

# location of domain whitelist
__cf = inspect.currentframe()
__p = os.path.dirname(os.path.abspath(inspect.getfile(__cf)))
__pw = os.path.join(__p, 'whitelist')
WHITELIST_LOC = __pw

__pc = os.path.join(__p, 'cache')
CACHE_LOC = __pc

# load domain whitelist
WHITELIST = set()
with open(WHITELIST_LOC) as fin:
    for line in fin:
        WHITELIST.add(line.decode('utf8').lower())
msg = "Loaded whitelist list with %d domains" % len(WHITELIST)
logging.info(msg)

# Create Custom Cache Extractor
EXTRACT = tldextract.TLDExtract(cache_file=CACHE_LOC)


def filter_urls(urls, whitelist=WHITELIST):
    """
    Returns only urls whose domain is in the whitelist
    """
    filtered = set()
    for url in urls:
        domain = EXTRACT(url).registered_domain.lower()
        logger.debug(u"%s" % domain)
        if domain in whitelist:
            filtered.add(url)
    return list(filtered)
