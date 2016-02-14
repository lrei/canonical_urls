"""
Tornado server
"""

import tornado
import logging
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.web import RequestHandler, MissingArgumentError
from canonicalurl import get_canonical_url_async


class MainHandler(RequestHandler):
    def initialize(self, whitelist, expandlist, extract, timeout, maxsize,
                   maxclients):
        self.whitelist = whitelist
        self.expandlist = expandlist
        self.extract = extract
        self.timeout = timeout
        self.maxsize = maxsize
        self.maxclients = maxclients

    @tornado.web.asynchronous
    def get_canonical(self, url):
        get_canonical_url_async(url, self.whitelist, self.expandlist,
                                self.extract, self.timeout, self.maxsize,
                                self.maxclients, self.write_data)

    def write_data(self, data):
        try:
            self.write(data)
        except Exception as ex:
            print(data)
            logging.exception(ex)
        self.finish()

    @tornado.web.asynchronous
    def get(self):
        try:
            url = self.get_query_argument('url')
            self.get_canonical(url)
        except MissingArgumentError:
            self.write({'error': 'no url query parameter'})
        except Exception as e:
            self.write({'error': str(e)})


def make_app(whitelist, expandlist, extract, timeout, maxsize, maxclients):
    d = {'whitelist': whitelist,
         'expandlist': expandlist,
         'extract': extract,
         'timeout': timeout,
         'maxsize': maxsize,
         'maxclients': maxclients}

    return tornado.web.Application([
        (r"/", MainHandler, d),
    ])


def serve(port, whitelist, expandlist, extract, timeout, maxsize, maxclients):
    app = make_app(whitelist, expandlist, extract, timeout)
    server = HTTPServer(app)
    server.bind(port)
    server.start(0)  # Forks multiple sub-processes
    IOLoop.current().start()
