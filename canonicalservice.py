#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Symphony Canonical URL Service
Luis Rei <luis.rei@ijs.si> @lmrei http://luisrei.com
version 1.1
10 Feb 2016

1 - Read configuration
2 - Setup (incl logging, whitelist, shorteners, ...)
2 - ZMQ Service
"""

import os
import argparse
import logging
import ConfigParser
import multiprocessing
import cPickle as pickle
from functools import partial
from zmqservice import serve, worker_task_builder
from canonicalurl import get_canonical_url, load_list, get_extractor


DEFAULT_PORT = 7171
ENV_PREFIX = 'CANONICALURL_'
DEFAULT_DIR = '/etc/canonicalurl/'
DEFAULT_CONFIG = 'canonicalurl.conf'
DEFAULT_NUM_WORKERS = multiprocessing.cpu_count() * 2


def init_config():
    """Setup configuration defaults
    """
    config = ConfigParser.RawConfigParser()
    config.add_section('service')

    # Service PORT
    config.set('service', 'port', DEFAULT_PORT)

    # Backend address
    BACKEND_ADDRESS = 'ipc://canonicalbackend.ipc'
    config.set('service', 'backend', BACKEND_ADDRESS)

    # Number of workers
    config.set('service', 'workers', DEFAULT_NUM_WORKERS)

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
    config.set('canonical', 'maxsize', 2 * 1024 * 1024)
    config.set('canonical', 'tldcache', './cache.tld') 


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
        confpaths.append(fenvpath)

    # Add default dir
    confpaths.append(os.path.join(DEFAULT_DIR, DEFAULT_CONFIG))

    # Home
    confpaths.append(os.path.join(os.path.expanduser('~/'), 
                                  '.' + DEFAULT_CONFIG))

    # current dir
    confpaths.append(os.path.join('./', DEFAULT_CONFIG))


    # Try each path until one returns
    for fpath in confpaths:
        if filepath is not None and os.path.isfile(fpath):
            try:
                config.read(filepath)
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
    loglevel = config.get('service', 'loglevel')

    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.setLevel(loglevel)

    ch = logging.FileHandler(logpath, encoding='utf8')
    formatter = logging.Formatter(FORMAT)
    ch.setFormatter(formatter)
    ch.setLevel(loglevel)

    root.addHandler(ch)
    """
    # General logging
    logging.basicConfig(filename=logpath, format=format_str, level=loglevel)


def load_lists(config):
    """Returns Whitelist, Shortner List
    """

    shortener_path = config.get('lists', 'shorteners')
    whitelist_path = config.get('lists', 'whitelist')

    whitelist = load_list(whitelist_path)
    shorteners = load_list(shortener_path)

    return whitelist, shorteners


def save_config(config, filepath):
    """Saves the current configuration to a file
    """
    with open(filepath, 'wb') as fout:
        config.write(fout)


def main():
    # Command line arguments
    parser = argparse.ArgumentParser(description='Run Canonical URL Service.')

    parser.add_argument('--port', type=int, default=0,
                        help='read/write to zmq socket at specified port')
    parser.add_argument('--workers', type=int, default=0,
                        help='number of concurrent workers')
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
    if args.workers > 0:
        config.set('service', 'workers', args.workers)
    if args.whitelist:
        config.set('lists', 'whitelist', args.whitelist)
    if args.shorteners:
        config.set('lists', 'shorteners', args.shorteners)

    # get final options
    port = config.get('service', 'port')
    n_workers = config.getint('service', 'workers')
    backend = config.get('service', 'backend')
    extr = get_extractor(config.get('canonical', 'tldcache')) 
    timeout = config.getint('canonical', 'timeout')
    maxsize = config.getint('canonical', 'maxsize')

    # Save config
    if args.save_config is not None:
        save_config(config, args.save_config)
    
    # Setup logging
    setup_logging(config)

    # Load Lists
    whitelist, shorteners = load_lists(config)

    # Setup worker function
    f = partial(get_canonical_url, whitelist=whitelist, expandlist=shorteners, 
                extract=extr, timeout=timeout, maxsize=maxsize)
    worker_task = worker_task_builder(f, backend)
    
    # Print PID
    m = 'Starting Canonical URL Service with PID: {}'.format(os.getpid())
    logging.info(m)

    # Run forever (or until kill -INT)
    serve(port, worker_task, n_workers, backend)


if __name__ == '__main__':
    main()
