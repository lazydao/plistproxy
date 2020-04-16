#!/usr/bin/env python
# coding: utf-8

import os
import time
import hashlib
import plistlib
import collections

import tornado
import tornado.ioloop
import tornado.web
import tornado.httpserver
from tornado import httpclient, ioloop
from tornado.options import define, options


define("port", default=int(os.environ.get('PORT', 8200)), help="Run server on a specific port", type=int) 

def get_bundle_id_from_plist_string(s):
    v = plistlib.loads(s)
    return v['items'][0]['metadata']['bundle-identifier']

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        token = self.get_argument('token', None)
        if not token:
            self.write("Hello, proxy")
            return
        else:
            if token != os.getenv('TOKEN'):
                raise tornado.web.HTTPError(403)
            self.write(PlistStoreHandler.bundle_ids)

class PlistStoreHandler(tornado.web.RequestHandler):
    db = {}
    bundle_ids = collections.defaultdict(list)

    def post(self):
        body = self.request.body
        if len(body) > 5000:
            self.set_status(500)
            self.finish("request body too long")
        bundle_id = get_bundle_id_from_plist_string(body)

        m = hashlib.md5()
        m.update(body)
        key = m.hexdigest()[8:16]
        self.db[key] = body
        self.write({'key': key, 'bundle_id': bundle_id})

    def get(self, key):
        value = self.db.get(key)
        if value is None:
            raise tornado.web.HTTPError(404)

        # update records
        bundle_id = get_bundle_id_from_plist_string(value)
        self.bundle_ids[bundle_id].append(self.request.remote_ip) # = view_count + 1

        self.set_header('Content-Type', 'text/xml')
        self.finish(value)


def make_app(debug=True):
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/plist/?", PlistStoreHandler),
        (r"/plist/(.+)", PlistStoreHandler),
    ], debug=debug)


if __name__ == "__main__":
    tornado.options.parse_command_line() 

    app = make_app(debug=bool(os.getenv('DEBUG')))
    server = tornado.httpserver.HTTPServer(app, xheaders=True)
    server.listen(options.port)
    print('Listening on port %d' % options.port)
    ioloop.IOLoop.current().start()
