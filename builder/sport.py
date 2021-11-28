def build_sport(src, type_matcher, config):
    iri = 'https://www.brno.cz/sportoviste/{}'.format(src.get('ogcfid'))

    ret = {
        '@context': 'https://ofn.gov.cz/sportoviště/2020-07-01/kontexty/sportoviště.jsonld',
        'typ': 'Sportoviště',
        'iri': iri,
        'název': {
            'cs': src.get('nazev')
        },   
    }

    description = src.get('popis')
    if description:
        ret['popis'] = {
            'cs': description
        }

    type = src.get('typ_sportoviste_nazev')
    ret['typ_sportoviště'] = ['https://data.mvcr.gov.cz/zdroj/číselníky/typy-sportovišť/položky/%s' % config['type_mapping'].get(type, 'jiné')]

    url = src.get('url')
    if url:
        if not url.startswith('http'):
            url = 'http://%s' % url

        ret['kontakt'] = [{
            'typ': 'Kontakt',
            'url': url.strip()
        }]

    x = float(src.get('longitude', 0))
    y = float(src.get('latitude', 0))
    address = src.get('address')

    if (x and y) or address:
        ret['umístění'] = {
            'typ': 'Umístění',
        }

    if x != 0 and y != 0:
        ret['umístění']['geometrie'] = {
                'type': 'Point',
                'coordinates': [x, y]
            }

    if address:
        ret['umístění']['adresa'] = {
            'typ': 'Adresa',
            'text': {
                'cs': address
            }
        }

    return ret


