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
        g.bind('vcard2006', VCARD2006)
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
        self.create_documentation(find(s, 'metadata.dataIdInfo.idCitation.otherCitDet') or find(s, 'landingPage'))

        return self.g

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
        if not value:
            return

        if type(value) == list:
            value = value[0]

        email = find(value, 'rpCntInfo.cntAddress.eMailAdd')

        if not email:
            email = self.config['defaults']['contact_email']

        bnode = BNode()

        if value.get('rpIndName'):
            self.g.add((bnode, RDF.type, VCARD2006.Individual))
            self.g.add((bnode, VCARD2006.fn, Literal(value.get('rpIndName'), lang='cs')))
        elif value.get('rpOrgName'):
            self.g.add((bnode, RDF.type, VCARD2006.Organization))
            self.g.add((bnode, VCARD2006.fn, Literal(value.get('rpOrgName'), lang='cs')))
        else:
            self.g.add((bnode, RDF.type, VCARD2006.Individual))
            self.g.add((bnode, VCARD2006.fn, Literal(self.config['defaults']['contact_email'], lang='cs')))

        self.g.add((bnode, VCARD2006.hasEmail, URIRef('mailto:{}'.format(email))))
        self.g.add((self.uri, DCAT.contactPoint, bnode))


    def create_distribution(self, value, source):
        types = self.config['mapping']['media']
        for d in value:
            if not 'accessURL' in d:
                continue

            if d['accessURL'] is None:
                continue

            if d['format'] in self.config['mapping']['ignore_format']:
                continue

            uri = URIRef(quote_url(d['accessURL']))
            is_service = False
            fmt = None
            media_type = None

            if d['format'] == 'Esri REST':
                is_service = True
                access_uri = uri + '/service'
                self.g.add((uri, DCAT.accessService, access_uri))
                self.g.add((access_uri, RDF.type, DCAT.DataService))
                self.g.add((access_uri, DCT.title, Literal(d['title'], lang=self.lang)))
                self.g.add((access_uri, DCAT.endpointURL, uri))
                self.g.add((access_uri, DCT.conformsTo, URIRef('urn:x-esri:serviceType:ArcGIS')))

            self.g.add((self.uri, DCAT.distribution, uri))
            self.g.add((uri, RDF.type, DCAT.Distribution))

            if not is_service:
                self.g.add((uri, DCAT.downloadURL, uri))


            format_name = (d.get('title') or '').split('(')[0].strip()

            if d.get('title'):
                self.g.add((uri, DCT.title, Literal(d['title'], lang=self.lang)))


            if format_name in types:
                fmt = types[format_name]['format']
                media_type = types[format_name]['mime']

            # Temporary fix (bug in source system)
            mediaType = d.get('mediaType')

            if not mediaType and not media_type:
                if d['format'] and re.match('^\w+/[\w+]+$', d['format']):
                    media_type = d['format']
                elif 'description' in d:
                    media_type = d['description']
                else:
                    media_type = 'application/octet-stream'
            elif mediaType:
                media_type = mediaType

            self.g.add((uri, DCAT.accessURL, uri))
            self.g.add((uri, DCAT.mediaType, URIRef('http://www.iana.org/assignments/media-types/{}'.format(media_type))))

            fmt_, compressed = self.types_matcher.find_match(d['format'], media_type)
            fmt_url = 'http://publications.europa.eu/resource/authority/file-type/{}'.format(fmt or fmt_)
            self.g.add((uri, DCT['format'], URIRef(fmt_url)))

            if compressed:
                self.g.add((uri, DCAT.compressFormat, URIRef('http://www.iana.org/assignments/media-types/{}'.format(media_type))))

            description = d.get('description')
            if description:
                ofn_url_test = r"https://ofn.gov.cz[^\s]+"

                res = re.search(ofn_url_test, description)

                if res:
                    self.g.add((uri, DCT.conformsTo, URIRef(res[0])))
                    self.g.add((self.uri, DCT.conformsTo, URIRef(res[0])))

                # if description contains more than just ofn uri, use it as description
                if not re.match(ofn_url_test, description):
                    self.g.add((uri, DCT.description, Literal(description)))

            self.create_license(uri, source)
