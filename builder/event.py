from datetime import datetime
from pytz import timezone
from ast import literal_eval

tz = timezone('Europe/Prague')

def build_event(src, type_matcher, config):
    ret = {
        '@context': 'https://ofn.gov.cz/události/2020-07-01/kontexty/událost.jsonld',
        'typ': 'Událost',
        'iri': src.get('url'),
        'název': {
            'cs': src.get('name')
        },
        'doba_trvání': [{
            'typ': 'Časová specifikace',
            'časový_interval': {
                'typ': 'Časový interval',
                'začátek': {
                    'typ': 'Časový okamžik',
                    'datum_a_čas': datetime.fromtimestamp(int(src.get('date_from')) / 1000, tz=tz).isoformat()
                },
                'konec': {
                    'typ': 'Časový okamžik',
                    'datum_a_čas': datetime.fromtimestamp(int(src.get('date_to')) / 1000, tz=tz).isoformat()
                }
            }
        }],
        'kontakt': [{
            'typ': 'Kontakt',
            'druh': {
                'cs': 'TIC, příspěvová organizace města',
                'en': 'TIC, Brno city-owned company',
            },
            'url': src.get('url',)
        }],
    }

    mail = src.get('organizer_email')
    if mail:
        ret['kontakt'][0]['email'] = 'mailto:%s' % mail 

    name_en = src.get('name_en')
    if name_en:
        ret['název']['en'] = name_en

    tickets = src.get('tickets_info', None) or src.get('tickets', None)

    if tickets:
        ret['vstupné'] = [{
            'typ': 'Vstupné',
            'podmínka': {
                'cs': tickets,
            },
        }]

    description = src.get('text')
    description_en = src.get('text_en')

    if description or description_en:
        ret['popis'] = {}

    if description:
        ret['popis']['cs'] = description

    if description_en:
        ret['popis']['en'] = description_en

    first_image = src.get('first_image')

    if first_image:
        ext = "."+ first_image.split("/")[-1:][0].split(".")[-1:][0]
        ret['příloha'] = [{
            'typ': 'Digitální objekt',
            'url': first_image,
            'vykonavatel_autorské_dílo': [{
                'typ': 'Osoba',
                'ičo': '00101460',
                'název': {
                    'cs': 'Turisticko informační centrum (TIC)'
                },
            }],
            'typ_média': type_matcher.match_by_extension(ext),
            'podmínky_užití': {
                'typ': 'Podmínky užití',
                'obsahuje_autorské_dílo': True,
                'obsahuje_více_autorských_děl': False,
                'licence_autorského_díla': 'https://creativecommons.org/licenses/by/4.0/',
                'originální_databáze': False,
                'ochrana_zvláštními_právy_pořizovatele_databáze': False,
                'obsahuje_osobní_údaje': False
            }
        }]

    parent_festivals = src.get('parent_festivals')
    if parent_festivals:
        ret['zaštiťující_událost'] = [{
            'typ': 'Událost',
            'iri': parent_festivals
        }]

    categories = (src.get('categories') or '').split(',')
    for category in categories:
        category = category.strip()
        category_type = config['category_mapping'].get(category)

        if category and category_type:
            ret.setdefault('typ_události', [])
            ret['typ_události'].append('https://data.mvcr.gov.cz/zdroj/číselníky/typy-událostí/položky/%s' % category_type)


    x = float(src.get('longitude', 0))
    y = float(src.get('latitude', 0))

    if x != 0 and y != 0:
        ret['umístění'] = [{
            'typ': 'Umístění',
            'geometrie': {
                'type': 'Point',
                'coordinates': [x, y]
            },
        }]

    return ret


