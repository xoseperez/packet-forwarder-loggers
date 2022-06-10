#!/usr/bin/env python

import os
import time
import threading
import sys
import flask
from flask import jsonify
from basicstation import parser as basicstation_parser
from legacy import parser as legacy_parser

PROTOCOL  = os.environ.get("PROTOCOL", "basicstation")
CONTAINER_NAME = os.environ.get("CONTAINER_NAME", "basicstation")
BUCKET_SIZE = int(os.environ.get("BUCKET_SIZE", 60))
BUCKET_COUNT = int(os.environ.get("BUCKET_COUNT", 15))

buckets = {}
totals = {
    'rx': 0,
    'tx': 0
}
previous_bucket = 0

def manage_buckets(timestamp):
    
    global totals
    global buckets
    global previous_bucket
    
    new_bucket = int(timestamp / BUCKET_SIZE)
    if new_bucket != previous_bucket:
        previous_bucket = new_bucket
        buckets = {key: value for key, value in buckets.items() if key > new_bucket - BUCKET_COUNT}
        buckets[new_bucket] = {
            'rx': 0,
            'tx': 0
        }
    return new_bucket


app = flask.Flask(__name__)
app.config["DEBUG"] = True

@app.route('/api/metrics', methods=['GET'])
def api_metrics():

    global totals
    global buckets
    global previous_bucket
    
    manage_buckets(time.time())
    offset = list(buckets.keys())[0]
    return jsonify(dict({
        'totals': totals,
        'buckets': { (key - offset): value for key, value in buckets.items() },
        'bucket_size': BUCKET_SIZE,
        'bucket_count': BUCKET_COUNT
    }))

threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8888, debug=True, use_reloader=False)).start()

if PROTOCOL == "basicstation":
    runner = basicstation_parser(CONTAINER_NAME, True)
elif PROTOCOL == "legacy":
    runner = legacy_parser(CONTAINER_NAME, True)
else:
    print("ERROR: Unkown protocol")
    sys.exit()

for value in runner.run():
    
    #print("Received: {}".format(value))
    
    bucket = manage_buckets(int(value['timestamp']))
    totals[value['type']] = totals[value['type']] + 1
    buckets[bucket][value['type']] = buckets[bucket][value['type']] + 1
