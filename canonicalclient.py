#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
import zmq
import json

def send_url(socket, url):
        socket.send(url)
        message = json.loads(socket.recv())
        return message


def main():
    url = sys.argv[1]
    address = 'tcp://localhost:' + str(7171)
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(address)
    res = send_url(socket, url)
    print(res)


if __name__ == '__main__':
    main()
