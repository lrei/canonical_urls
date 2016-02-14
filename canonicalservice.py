#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Symphony Canonical URL Service
Luis Rei <luis.rei@ijs.si> @lmrei http://luisrei.com
version 1.2
12 Feb 2016
"""

import os
import argparse
import logging
import ConfigParser
from domainlists import load_list, get_extractor
from server import serve


DEFAULT_PORT = 7171
ENV_PREFIX = 'CANONICALURL_'
DEFAULT_DIR = '/etc/canonicalurl/'
DEFAULT_CONFIG = 'canonicalurl.cfg'


def init_config():
    """Setup configuration defaults
    """
    config = ConfigParser.RawConfigParser()
    config.add_section('service')

    # Service PORT
    config.set('service', 'port', DEFAULT_PORT)

    # logging
    config.set('service', 'log', '/tmp/canonical.log')
    config.set('service', 'loglevel', logging.DEBUG)

    # Lists
    config.add_section('lists')

    config.set('lists', 'shorteners', './shorteners.txt')
    config.set('lists', 'whitelist', './whitelist.txt')

    # Canonical URL extraction
    config.add_section('canonical')

    config.set('canonical', 'timeout', 30)
    config.set('canonical', 'maxsize', 2097152)
    config.set('canonical', 'maxclients', 100)
    config.set('canonical', 'tldcache', './cache.tld')

    # return
    return config


def read_config_file(config, filepath=None):
    """Reads configuration from a file. Searches paths for file
    """

    # List of possible configuration paths
    confpaths = []

    # Add argument filepath
    if filepath is not None:
        confpaths.append(filepath)

    # Add environment filepath
    envpath = os.getenv(ENV_PREFIX+'CONFIG', None)
    if envpath is not None:
        confpaths.append(envpath)

    # Add default dir
    confpaths.append(os.path.join(DEFAULT_DIR, DEFAULT_CONFIG))

    # Home
    confpaths.append(os.path.join(os.path.expanduser('~/'),
                                  '.' + DEFAULT_CONFIG))

    # current dir
    confpaths.append(os.path.join('./', DEFAULT_CONFIG))

    # Try each path until one returns
    for fpath in confpaths:
        if fpath is not None and os.path.isfile(fpath):
            try:
                config.read(fpath)
                return config
            except:
                pass

    # If none return, just spit the default back out
    return config


def setup_logging(config):
    """Sets up logging
    """
    format_str = "%(asctime)-15s %(process)d: %(message)s"
    logpath = config.get('service', 'log')
    loglevel = config.getint('service', 'loglevel')

    # General logging
    logging.basicConfig(filename=logpath, filemode='w',
                        format=format_str, level=loglevel)


def load_lists(config):
    """Returns Whitelist, Shortner List
    """
    whitelist = None
    shorteners = None

    shortener_path = config.get('lists', 'shorteners')
    whitelist_path = config.get('lists', 'whitelist')

    try:
        whitelist = load_list(whitelist_path)
    except Exception as ex:
        logging.exception(ex)
        whitelist = None

    try:
        shorteners = load_list(shortener_path)
    except Exception as ex:
        logging.exception(ex)
        shorteners = None

    return whitelist, shorteners


def save_config(config, filepath):
    """Saves the current configuration to a file
    """
    with open(filepath, 'wb') as fout:
        config.write(fout)


def main():
    """Main: Parses command line arguments, loads configs and runs app
    """
    # Command line arguments
    parser = argparse.ArgumentParser(description='Run Canonical URL Service.')

    parser.add_argument('--port', type=int, default=0,
                        help='read/write to zmq socket at specified port')
    parser.add_argument('--config', type=str, default=None,
                        help='configuration file')
    parser.add_argument('--whitelist', type=str, default=None,
                        help='whitelisted URL file')
    parser.add_argument('--shorteners', type=str, default=None,
                        help='URL shorteners file')
    parser.add_argument('--save-config', type=str, default=None,
                        help='Export configuration to this file')

    # Parse
    args = parser.parse_args()

    # Defaul Config
    config = init_config()
    # Load File
    config = read_config_file(config, filepath=args.config)

    if args.port > 0:
        config.set('service', 'port', args.port)
    if args.whitelist:
        config.set('lists', 'whitelist', args.whitelist)
    if args.shorteners:
        config.set('lists', 'shorteners', args.shorteners)

    # get final options
    port = config.get('service', 'port')
    extr = get_extractor(config.get('canonical', 'tldcache'))
    timeout = config.getint('canonical', 'timeout')
    maxsize = config.getint('canonical', 'maxsize')
    maxclients = config.getint('canonical', 'maxclients')

    # Save config
    if args.save_config is not None:
        save_config(config, args.save_config)

    # Setup logging
    setup_logging(config)

    # Load Lists
    whitelist, shorteners = load_lists(config)

    serve(port, whitelist, shorteners, extr, timeout, maxsize, maxclients)


if __name__ == '__main__':
    main()
