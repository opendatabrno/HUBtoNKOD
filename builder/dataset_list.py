from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import DCAT, RDF
from builder.dataset_detail import find

DCT = Namespace("http://purl.org/dc/terms/")

def dataset_list(src, url, base, config, extension):

    def has_distributions(d):
        return 'accessURL' in d \
            and d['format'] not in config['mapping']['ignore_format']

    g = Graph()
    g.bind('dcat', DCAT)
    g.bind('dct', DCT)

    uri = URIRef(url)
    g.add((uri, RDF.type, DCAT.Catalog))

    for lang, text in  config['catalog']['name'].items():
        g.add((uri, DCT.title, Literal(text, lang=lang)))

    for lang, text in  config['catalog']['description'].items():
        g.add((uri, DCT.description, Literal(text, lang=lang)))

    g.add((uri, DCT.publisher, URIRef(config['opendata']['publisher'])))

    for dataset in src['dataset']:
        license = dataset.get('license')

        if license not in config['mapping']['license']:
            continue

        distributions = find(dataset, 'distribution') or []
        distributions = list(filter(has_distributions, distributions))
        onLineSrc = find(dataset, 'metadata.distInfo.distTranOps.onLineSrc') or []

        if len(onLineSrc) == 0 and len(distributions) == 0:
            continue

        dataset_id = dataset['identifier'].split('/')[-1]
        dataset_uri = '{}nkod/dataset/{}{}'.format(base, dataset_id, extension)
        g.add((uri, DCAT.dataset, URIRef(dataset_uri)))

    return g
