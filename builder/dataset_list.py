from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import DCAT, RDF

DCT = Namespace("http://purl.org/dc/terms/")

def dataset_list(src, url, base, config):
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

        dataset_id = dataset['identifier'].split('/')[-1]
        dataset_uri = '{}nkod/dataset/{}.ttl'.format(base, dataset_id)
        g.add((uri, DCAT.dataset, URIRef(dataset_uri)))

    return g.serialize(format='turtle').decode()
