days = {
    1: 'pondělí',
    2: 'úterý',
    3: 'středa',
    4: 'čtvrtek',
    5: 'pátek',
    6: 'sobota',
    7: 'neděle',
}

frequency = {
    '7': 'WEEKLY',
    '14': 'BIWEEKLY',
    '30': 'MONTHLY'
}

def map_waste_type(type, mappings):
    ret = []
    if type in mappings:
        for t in mappings[type].split(','):
            ret.append('https://data.mvcr.gov.cz/zdroj/číselníky/typy-tříděného-odpadu/položky/{}'.format(t.strip()))

    return ret

def get_owner(owner, owners):
    if not owner:
        return None

    if owner in owners:
        o = owners[owner]
        return {
            'typ': 'Osoba',
            'ičo': str(o['ico']),
            'název': {
                'cs': o['name']
            }
        }
    elif 'městská část Brno' in owner:
        return {
            'typ': 'Osoba',
            'ičo': str(owners['_brno']['ico']),
            'název': {
                'cs': owner
            }
        }

    return None

def get_pickup(item):
    ret = []

    for day in range(1,8):
        d = 'vyvoz_{}'.format(day)
        f = 'vyvoz_{}_interval'.format(day)

        if item[f] in frequency:
            f = frequency[str(item[f])]
        else:
            f = 'IRREG'

        if item[d] == 'A':
            ret.append({
                'den_v_týdnu': [
                    'https://data.mvcr.gov.cz/zdroj/číselníky/dny-v-týdnu/položky/{}'.format(days[day])
                ],
                'frekvence': [
                    'http://publications.europa.eu/resource/authority/frequency/{}'.format(f)
                ]
            })

    return ret

def build_container(src, config):
    attr = src.get('attributes')
    geo = src.get('geometry')
    iri = 'https://www.brno.cz/container/{}'.format(attr.get('tid'))

    ret = {
        '@context': 'https://pod-test.mvcr.gov.cz/otevřené-formální-normy/nádoby-na-tříděný-odpad/draft/kontexty/nádoby-na-tříděný-odpad.jsonld',
        'typ': 'Nádoba na tříděný odpad',
        'iri': iri,
        'stanoviště_pro_nádoby': {
            'typ': 'Stanoviště pro nádoby na tříděný odpad',
            'iri': 'https://www.brno.cz/container-station/{}'.format(attr.get('stanoviste_ogc_fid')),
                
        },
        'časy_vývozu': get_pickup(attr)
    }

    waste_type = map_waste_type(attr.get('komodita_odpad_separovany'), config['waste_mapping'])
    if waste_type:
        ret['typ_tříděného_odpadu'] = waste_type

    public = attr.get('verejnost')
    if public:
        ret['veřejná_přístupnost'] = public == 'A'


    volume = attr.get('objem')
    if volume:
        ret['objem'] = {
            'typ': 'Množství',
            'hodnota': volume,
            'jednotka': 'LTR'
        }

    owner = get_owner(attr.get('majitel'), config['owners'])
    if owner:
        ret['správce'] = owner

    x = float(geo.get('x', 0))
    y = float(geo.get('y', 0))

    if x != 0 and y != 0:
        ret['stanoviště_pro_nádoby']['umístění'] = [{
            'typ': 'Umístění',
            'geometrie': {
                'type': 'Point',
                'coordinates': [x, y]
            },
        }]

    return ret


