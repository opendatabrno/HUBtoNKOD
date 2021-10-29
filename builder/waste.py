def build_waste(src):
    attr = src.get('attributes')
    geo = src.get('geometry')
    iri = 'https://www.brno.cz/sso/{}'.format(attr.get('id_sso').replace('#', ''))

    ret = {
        '@context': 'https://pod-test.mvcr.gov.cz/otevřené-formální-normy/sběrné-dvory/draft/kontexty/sběrné-dvory.jsonld',
        'typ': 'Sběrný dvůr',
        'iri': iri,
        'název': {
            'cs': attr.get('nazev_sso')
        },
    }

    x = float(geo.get('x', 0))
    y = float(geo.get('y', 0))

    if x != 0 and y != 0:
        ret['umístění'] = [{
            'typ': 'Umístění',
            'geometrie': {
                'type': 'Point',
                'coordinates': [x, y]
            },
        }]

    return ret


