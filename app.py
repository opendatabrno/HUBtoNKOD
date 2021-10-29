import requests
import requests_cache
from flask import Flask, Response, request, abort
from builder.dataset_list import *
from builder.dataset_detail import Builder
from builder.filetypes import TypeMatcher
from builder.event import build_event
from builder.waste import build_waste
from builder.container import build_container
from datetime import timedelta
from yaml import load, SafeLoader
import lxml.etree as ET
from functools import wraps
from werkzeug.exceptions import NotAcceptable
from json import dumps

app = Flask(__name__)


with open('config.yaml', 'r') as c:
    config = load(c, Loader=SafeLoader)

SOURCE_URL = config['opendata']['url']

expire_after = timedelta(minutes=config['cache']['timeout'])
requests_cache.install_cache(expire_after=expire_after, backend='memory')

with ET.open('filetypes.xml', 'r') as x:
    filetypes_src = ET.parse(x)
    types_matcher = TypeMatcher(filetypes_src)


ext_mapping = {
    'ttl': {'mime': 'text/turtle', 'format': 'turtle'},
    'jsonld': {'mime': 'application/ld+json', 'format': 'json-ld'},
    'json': {'mime': 'application/json', 'format': 'json-ld'}
}
mime_mapping = {m['mime']: m['format'] for m in ext_mapping.values()}

def mime_choose(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ext = kwargs.get('extension', None)

        if ext in ext_mapping:
            t = ext_mapping[ext]
            return fn(*args, return_mime=t['mime'], format=t['format'],**kwargs)
        elif request.accept_mimetypes.values():
            for mimetype in request.accept_mimetypes.values():
                if mimetype in mime_mapping:
                    format = mime_mapping[mimetype]
                    return fn(*args, return_mime=mimetype, format=format,**kwargs)
                if mimetype == '*/*':
                    return fn(*args, return_mime='text/turtle', format='turtle',**kwargs)
            raise NotAcceptable
        else:
            raise NotAcceptable

    return wrapper

@app.route('/nkod/index.<extension>')
@app.route('/nkod/index', defaults={'extension': ''})
@mime_choose
def index(return_mime, format, extension):

    url = request.url
    url_root = request.url_root

    if config['server']['ssl']:
        url = url.replace('http://', 'https://')
        url_root = url_root.replace('http://', 'https://')

    src = requests.get(SOURCE_URL).json()
    ext = '.' + extension if extension else ''
    res = dataset_list(src, url, url_root, config, ext)
    return Response(res.serialize(format=format), mimetype=return_mime)

@app.route('/nkod/dataset/<dataset>.<extension>')
@app.route('/nkod/dataset/<dataset>', defaults={'extension': ''})

@mime_choose
def detail(dataset, return_mime, format, extension):
    src = requests.get(SOURCE_URL).json()

    url = request.url

    if config['server']['ssl']:
        url = url.replace('http://', 'https://')

    for d in src['dataset']:
        dataset_id = d['identifier'].split('/')[-1]
        if dataset_id == dataset:
            builder = Builder(d, url, config, types_matcher).create_dataset()
            return Response(builder.serialize(format=format), mimetype=return_mime)

    abort(404)

@app.route('/nkod/ofn/events.json')
def events():
    url = config['ofn']['events']['url']
    src = requests.get(url).json()

    res = []

    for item in src.get('features'):
        res.append(build_event(item.get('attributes'), types_matcher))

    return Response(dumps(res, ensure_ascii=False), mimetype='application/json')

@app.route('/nkod/ofn/waste.json')
def waste():
    url = config['ofn']['waste']['url']
    src = requests.get(url).json()

    res = []

    for item in src.get('features'):
        res.append(build_waste(item))

    return Response(dumps(res, ensure_ascii=False), mimetype='application/json')

@app.route('/nkod/ofn/container.json')
def container():
    url = config['ofn']['container']['url']
    src = requests.get(url).json()

    res = []

    for item in src.get('features'):
        res.append(build_container(item, config['ofn']['container']))

    return Response(dumps(res, ensure_ascii=False), mimetype='application/json')


if __name__ == '__main__':
    app.run(port=config['server']['port'])
