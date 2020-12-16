import requests
import requests_cache
from flask import Flask, Response, request, abort
from builder.dataset_list import *
from builder.dataset_detail import Builder
from datetime import timedelta
from yaml import load, SafeLoader


app = Flask(__name__)


with open('config.yaml', 'r') as c:
    config = load(c, Loader=SafeLoader)

SOURCE_URL = config['opendata']['url']

expire_after = timedelta(minutes=config['cache']['timeout'])
requests_cache.install_cache(expire_after=expire_after, backend='memory')


@app.route('/nkod/index.ttl')
def index():
    src = requests.get(SOURCE_URL).json()
    return Response(dataset_list(src, request.url, request.url_root, config), mimetype='text/turtle')

@app.route('/nkod/dataset/<dataset>.ttl')
def detail(dataset):
    src = requests.get(SOURCE_URL).json()

    for d in src['dataset']:
        dataset_id = d['identifier'].split('/')[-1]
        if dataset_id == dataset:
            builder = Builder(d, request.url, config)
            return Response(builder.create_dataset(), mimetype='text/turtle')

    abort(404)

if __name__ == '__main__':
    app.run(port=config['server']['port'])
