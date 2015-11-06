'''
Author: Luis Rei <luis.rei@ijs.si>
This script reads a list of URLs from a file (line delimited) and attempts 
to fetch the canonical urls, outputs to stdout.

Requirements:
futures

To get a list of urls from a json-ld file try something like:
jq -r ".urls |  .[]" batch0.txt > urls.txt

'''

import sys
import json
import time
import logging
import concurrent.futures
from multiprocessing import cpu_count

from canonical_urls.canonicalurl import get_canonical_url


logging.basicConfig(level=logging.INFO)


POOL_SIZE = cpu_count() * 15


def worker(url):
    if not isinstance(url, unicode):
        try:
            url = url.decode('utf8')
        except Exception as e:
            logging.exception(e)
            return None

    try:
        ori, res, met = get_canonical_url(url)
    except Exception as e:
        msg = '%s : %s' % (url.encode('utf8'), e)
        logging.exception(msg)
        return None

    if ori == None or res == None:
        return None

    return json.dumps({'original': ori, 'result': res, 'method': met})


def main():

    # read file
    logging.info('Reading file')
    fin = open(sys.argv[1])
    urls = fin.readlines()
    fin.close()

    # unique urls
    logging.info('Unique urls')
    urls = [x.strip().decode('utf8') for x in urls]
    urls = list(set(urls))
    total_size = len(urls)

    # Discard urls with login @TODO

    # start
    logging.info('Starting: %d' % (total_size,))

    count = 0
    last_count = 0
    failed = 0
    start_time = time.time()



    with open(sys.argv[2], 'w') as destination:
        with concurrent.futures.ProcessPoolExecutor(POOL_SIZE) as executor:
            for line in executor.map(worker, urls):
                # stats
                count += 1
                if line is None:
                    failed += 1
                if count - last_count > 500:
                    last_count = count
                    remaining = total_size - count
                    cur_time = time.time()
                    speed = count / (cur_time - start_time)
                    eta = remaining / speed
                    eta = eta / 3600.0
                    msg = 'Done: {}\tFailed: {}\tRemaining: {} ({}h)'
                    msg = msg.format(count, failed, remaining, eta)
                    logging.info(msg)

                # write to disk
                if line is not None:
                    destination.write(line + '\n')
                destination.flush()


if __name__ == '__main__':
    main()
