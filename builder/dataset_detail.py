import operator
import xml.etree.ElementTree as ET
from rdflib import URIRef, Graph, Literal, Namespace, XSD, BNode
from rdflib.namespace import DCAT, RDF, DC, FOAF
from urllib.parse import quote
from isodate import parse_datetime

DCT = Namespace("http://purl.org/dc/terms/")
VCARD2006 = Namespace('http://www.w3.org/2006/vcard/ns#')
PU = Namespace('https://data.gov.cz/slovník/podmínky-užití/')

def find(element, path):
    parts = path.split('.')
    obj = element
    try:
        for p in parts:
            obj = obj.get(p, {})

        return obj or None
    except:
        return None

def quote_url(url):
    return quote(url, safe="%/:=&?~#+!$,;'@()*[]")

class Builder():

    def __init__(self, source, uri, config):
        self.g = Graph()
        self.s = source
        self.url = uri
        self.uri = URIRef(uri)
        self.lang = 'cs'
        self.config = config

    def create_dataset(self):
        g = self.g
        s = self.s

        g.bind('dcat', DCAT)
        g.bind('dc', DC)
        g.bind('dct', DCT)
        g.bind('vcard2006', VCARD2006)
        g.bind('foaf', FOAF)
        g.bind('pu', PU)

        src_uri = URIRef(self.uri)

        g.add((self.uri, RDF.type, DCAT.Dataset))
        g.add((self.uri, DCT.title, Literal(s.get('title'), lang=self.lang)))
        g.add((self.uri, DCT.description, Literal(s.get('description'), lang=self.lang)))
        g.add((self.uri, DCT.publisher, URIRef(self.config['opendata']['publisher'])))

        for keyword in s.get('keyword', []):
            g.add((src_uri, DCAT.keyword, Literal(keyword, lang=self.lang)))

        self.create_modified(s.get('modified'))
        self.create_publisher(find(s, 'publisher.name'))
        self.map_category(s.get('category', []))
        self.map_period(find(s, 'metadata.dataIdInfo.resMaint.maintFreq.MaintFreqCd.@_value'))
        self.map_spatial(find(s, 'metadata.dataIdInfo.dentCode'))
        self.create_contact(s.get('contactPoint', {}))
        self.create_distribution(s.get('distribution', []), s)
        self.create_online_src(find(s, 'metadata.distInfo.distTranOps.onLineSrc'), s)
        self.create_documentation(find(s, 'metadata.dataIdInfo.idCitation.otherCitDet'))

        return self.g.serialize(format='turtle').decode()


    def create_license(self, uri, source):
        license_defaults = self.config['license_defaults']

        bnode = BNode()
        for key, url in license_defaults.items():
            self.g.add((bnode, PU[key], URIRef(url)))


        license = find(s,'license')
        license_link = self.config['mapping']['license'][license]
        self.g.add((bnode, PU['autorské-dílo', URIRef(license_link)]))

        self.g.add((bnode, RDF.type, PU.Specifikace))
        self.g.add((uri, PU.specifikace, bnode))

    def create_documentation(self, value):
        if value:
            self.g.add((self.uri, FOAF.page, URIRef(value)))

    def create_modified(self, value):
        if value:
            v = parse_datetime(value)
            self.g.add((self.uri, DCT.modified, Literal(v, datatype=XSD.dateTime)))

    def create_publisher(self, value):
        if value:
            self.g.add((self.uri, DCT.publisher, Literal(value)))

    def create_page(self, value):
        if value:
            self.g.add((self.uri, FOAF.page, URIRef(value)))

    def map_spatial(self, value):
        self.g.add((self.uri, DCT.spatial, URIRef('https://linked.cuzk.cz/resource/ruian/')))

    def map_category(self, value):
        if not type(value) == list:
            value = [value]

        theme = self.config['mapping']['theme']

        for v in value:
            if v in theme:
                uri = URIRef('http://publications.europa.eu/resource/authority/data-theme/{}'.format(theme[v]))
                self.g.add((self.uri, DCAT.theme, uri))

    def map_period(self, value):
        periodicity = self.config['mapping']['periodicity']

        if value and value in periodicity:
            uri = URIRef('http://publications.europa.eu/resource/authority/frequency/{}'.format(periodicity[value]))
            self.g.add((self.uri, DCT.accrualPeriodicity, uri))

    def create_contact(self, value):
        if 'fn' not in value and 'hasEmail' not in value:
            return

        contact_uri = URIRef('{}/contact-point'.format(self.url))

        self.g.add((self.uri, DCT.contactPoint, contact_uri))

        self.g.add((contact_uri, RDF.type, VCARD2006.Organization))

        if 'fn' in value:
            self.g.add((contact_uri, VCARD2006.fn, Literal(value['fn'], lang='cs')))

        if 'hasEmail' in value:
            self.g.add((contact_uri, VCARD2006.hasEmail, Literal(value['hasEmail'])))

    def create_distribution(self, value, source):
        for d in value:
            if not 'accessURL' in d:
                continue

            uri = URIRef(quote_url(d['accessURL']))

            self.g.add((self.uri, DCAT.distribution, uri))
            self.g.add((uri, RDF.type, DCAT.distribution))

            self.g.add((uri, DCAT.downloadURL, uri))
            self.g.add((uri, DCAT.accessURL, uri))
            self.g.add((uri, DCAT.mediaType, Literal(d['mediaType'].replace('/', ':'))))
            self.create_license(uri, source)

    def create_online_src(self, value, source):
        if not value:
            return

        if not isinstance(value, list):
            value = [value]

        types = self.config['mapping']['media']

        for d in value:
            if not 'linkage' in d:
                continue

            uri = URIRef(quote_url(d['linkage']))

            self.g.add((self.uri, DCAT.distribution, uri))
            self.g.add((uri, RDF.type, DCAT.distribution))

            self.g.add((uri, DCAT.downloadURL, uri))
            self.g.add((uri, DCAT.accessURL, uri))

            src_type = d.get('orName', '').lower()
            mediaType = types.get(src_type, 'application/octet-stream')

            self.g.add((uri, DCAT.mediaType, Literal('http://www.iana.org/assignments/media-types/{}'.format(mediaType))))

            self.create_license(uri, source)
