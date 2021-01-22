import operator
import xml.etree.ElementTree as ET
from rdflib import URIRef, Graph, Literal, Namespace, XSD, BNode
from rdflib.namespace import DCAT, RDF, DC, FOAF
from urllib.parse import quote
from isodate import parse_datetime
from flask import Markup
from bs4 import BeautifulSoup
import re


DCT = Namespace("http://purl.org/dc/terms/")
VCARD = Namespace('http://www.w3.org/2006/vcard/ns#')
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

    def __init__(self, source, uri, config, types_matcher):
        self.g = Graph()
        self.s = source
        self.url = uri
        self.uri = URIRef(uri)
        self.lang = 'cs'
        self.config = config
        self.types_matcher = types_matcher

    def create_dataset(self):
        g = self.g
        s = self.s

        g.bind('dcat', DCAT)
        g.bind('dc', DC)
        g.bind('dct', DCT)
        g.bind('vcard', VCARD)
        g.bind('foaf', FOAF)
        g.bind('pu', PU)

        src_uri = URIRef(self.uri)

        g.add((self.uri, RDF.type, DCAT.Dataset))
        title = s.get('title').split('/')
        g.add((self.uri, DCT.title, Literal(title[0].strip(), lang=self.lang)))

        if len(title) > 1:
            g.add((self.uri, DCT.title, Literal(title[1].strip(), lang='en')))

        g.add((self.uri, DCT.description, Literal(Markup(s.get('description') or '').striptags(), lang=self.lang)))
        g.add((self.uri, DCT.publisher, URIRef(self.config['opendata']['publisher'])))

        for keyword in s.get('keyword', []):
            g.add((src_uri, DCAT.keyword, Literal(keyword, lang=self.lang)))

        self.create_modified(s.get('modified'))
        self.create_publisher(find(s, 'publisher.name'))
        self.map_category(s.get('category', []))
        self.map_period(find(s, 'metadata.dataIdInfo.resMaint.maintFreq.MaintFreqCd.@_value'))
        self.map_spatial(find(s, 'metadata.dataIdInfo.dataExt.geoEle.GeoDesc.geoId.identCode'))
        self.create_contact(find(s, 'metadata.dataIdInfo.idPoC'))
        self.create_distribution(s.get('distribution', []), s)
        self.create_online_src(find(s, 'metadata.distInfo.distTranOps.onLineSrc'), s)
        self.create_documentation(find(s, 'metadata.dataIdInfo.idCitation.otherCitDet'), s.get('description') or '')

        return self.g.serialize(format='turtle').decode()


    def create_license(self, uri, source):
        license_defaults = self.config['license_defaults']

        bnode = BNode()
        for key, url in license_defaults.items():
            self.g.add((bnode, PU[key], URIRef(url)))


        license = find(self.s,'license')
        license_link = self.config['mapping']['license'][license]
        self.g.add((bnode, PU['autorské-dílo'], URIRef(license_link)))

        author = find(source, 'publisher.source')
        if author:
            self.g.add((bnode, PU.autor, Literal(author, lang='cs')))

        self.g.add((bnode, RDF.type, PU.Specifikace))
        self.g.add((uri, PU.specifikace, bnode))

    def create_documentation(self, value, description):
        if value:
            self.g.add((self.uri, FOAF.page, URIRef(value)))

        # search dataset description for extra link to documentation
        soup = BeautifulSoup(description, features='html.parser')
        link = soup.find('a', text=re.compile(self.config['strings']['documentation_link'], re.I))

        if link:
            self.g.add((self.uri, FOAF.page, URIRef(link['href'])))


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
        if value:
            _type = self.config['mapping']['ruian'][value]
            self.g.add((self.uri, DCT.spatial, URIRef('https://linked.cuzk.cz/resource/ruian/{}/{}'.format(_type, value))))

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
        email = find(value, 'rpCntInfo.cntAddress.eMailAdd')

        if not email:
            email = self.config['defaults']['contact_email']

        contact_uri = URIRef('{}/contact-point'.format(self.url))

        self.g.add((self.uri, DCT.contactPoint, contact_uri))

        if value.get('rpIndName'):
            self.g.add((contact_uri, RDF.type, VCARD.Individual))
            self.g.add((contact_uri, VCARD.fn, Literal(value.get('rpIndName'), lang='cs')))
        elif value.get('rpOrgName'):
            self.g.add((contact_uri, RDF.type, VCARD.Organization))
            self.g.add((contact_uri, VCARD.fn, Literal(value.get('rpOrgName'), lang='cs')))
        else:
            self.g.add((contact_uri, RDF.type, VCARD.Individual))
            self.g.add((contact_uri, VCARD.fn, Literal(self.config['defaults']['contact_email'], lang='cs')))

        self.g.add((contact_uri, VCARD.hasEmail, Literal(email)))


    def create_distribution(self, value, source):
        for d in value:
            if not 'accessURL' in d:
                continue

            if d['format'] in self.config['mapping']['ignore_format']:
                continue

            uri = URIRef(quote_url(d['accessURL']))

            if d['format'] == 'Esri REST':
                self.g.add((self.uri, DCAT.dataService, uri))
                self.g.add((uri, RDF.type, DCAT.DataService))
                self.g.add((uri, DCT.title, Literal(d['title'], lang=self.lang)))
                self.g.add((uri, DCAT.endpointURL, uri))
                self.g.add((uri, DCT.conformsTo, URIRef('urn:x-esri:serviceType:ArcGIS')))
                continue

            self.g.add((self.uri, DCAT.distribution, uri))
            self.g.add((uri, RDF.type, DCAT.Distribution))

            self.g.add((uri, DCAT.downloadURL, uri))
            self.g.add((uri, DCAT.accessURL, uri))
            self.g.add((uri, DCAT.mediaType, URIRef('http://www.iana.org/assignments/media-types/{}'.format(d['mediaType']))))

            fmt, compressed = self.types_matcher.find_match(d['format'], d['mediaType'])
            self.g.add((uri, DCT['format'], URIRef(fmt)))

            if compressed:
                self.g.add((uri, DCAT.compressFormat, URIRef('http://www.iana.org/assignments/media-types/{}'.format(d['mediaType']))))

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

            if d['linkage'].endswith('FeatureServer') and 'orName' not in d:
                self.g.add((self.uri, DCAT.dataService, uri))
                self.g.add((uri, RDF.type, DCAT.DataService))
                self.g.add((uri, DCT.title, Literal('Esri Rest API', lang=self.lang)))
                self.g.add((uri, DCAT.endpointURL, uri))
                self.g.add((uri, DCT.conformsTo, URIRef('urn:x-esri:serviceType:ArcGIS')))
                continue

            if 'orName' in d:
                name = d['orName'].split('(')[0].split('-')[0].strip()

                if name in types:
                    fmt = types[name]['format']
                    mime = types[name]['mime']
                else:
                    continue


            self.g.add((self.uri, DCAT.distribution, uri))
            self.g.add((uri, RDF.type, DCAT.Distribution))

            self.g.add((uri, DCAT.downloadURL, uri))
            self.g.add((uri, DCAT.accessURL, uri))

            self.g.add((uri, DCAT.mediaType, URIRef('http://www.iana.org/assignments/media-types/{}'.format(mime))))
            self.g.add((uri, DCT['format'], URIRef('http://publications.europa.eu/resource/authority/file-type/{}'.format(fmt))))

            fmt, compressed = self.types_matcher.find_match(None, mime)
            if compressed:
                self.g.add((uri, DCAT.compressFormat, URIRef('http://www.iana.org/assignments/media-types/{}'.format(mime))))

            # last attempt to recognize compression
            if not compressed and d['linkage'].endswith('.zip') :
                self.g.add((uri, DCAT.compressFormat, URIRef('http://www.iana.org/assignments/media-types/application/zip')))

            self.create_license(uri, source)
