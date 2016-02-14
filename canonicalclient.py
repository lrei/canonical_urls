#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
import json
import time
import requests
import tornado.ioloop
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat


testurls = ['https://t.co/gFVKpELNO0',
            'https://docs.python.org/2/library/configparser.html',
            'http://www.huffingtonpost.com/entry/clinton-sanders-debate_us_56bd67d2e4b0b40245c60e1f',
            'http://edition.cnn.com/2016/02/11/entertainment/taylor-swift-kanye-west-new-song/index.html',
            'http://www.nytimes.com/2016/02/11/technology/twitter-to-save-itself-must-scale-back-world-swallowing-ambitions.html?ref=technology',
            'http://blogs.sciencemag.org/pipeline/archives/2012/07/31/synthetic_chemistry_the_rise_of_the_algorithms',
            'http://bbc.in/1Xlrix7',
            'https://t.co/MefZPI6SNw',
        ]


def handle_request(response):
    if response.error:
        print "Error:", response.error
    else:
        print type(response.body)
        print(json.loads(response.body))


def async_client(address):
    http_client = AsyncHTTPClient()

    for testurl in testurls:
        params = {"url": testurl}
        url = url_concat(address, params)
        print(url)
        http_client.fetch(url, handle_request)

    tornado.ioloop.IOLoop.instance().start()


def sync_client(address):
    for testurl in testurls:
        params = {"url": testurl}
        r = requests.get(address, params=params)
        print(r.json())


def main():
    port = sys.argv[1]
    address = 'http://localhost:' + port

    sync_client(address)
    #async_client(address)
    
if __name__ == '__main__':
    main()
