from datetime import datetime
from pytz import timezone

tz = timezone('Europe/Prague')

def build_event(src, type_matcher):
    ret = {
        '@context': 'https://ofn.gov.cz/události/2020-07-01/kontexty/událost.jsonld',
        'typ': 'Událost',
        'iri': src.get('url'),
        'název': {
            'cs': src.get('name')
        },
        'popis': {
            'cs': src.get('text')
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

    tickets = src.get('tickets_info', None) or src.get('tickets', None)

    if tickets:
        ret['vstupné'] = [{
            'typ': 'Vstupné',
            'podmínka': {
                'cs': tickets,
            },
        }]

    first_image = src.get('first_image')

    if first_image:
        ext = "."+ first_image.split("/")[-1:][0].split(".")[-1:][0]
        ret['příloha'] = [{
            'typ': 'Digitální objekt',
            'url': first_image,
            'autor_díla': [{
                'typ': 'Příspěvková organizace města Brna',
                'jméno': {
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


