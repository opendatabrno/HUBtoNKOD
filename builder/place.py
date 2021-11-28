from datetime import datetime
from pytz import timezone
from phonenumbers.phonenumberutil import format_number
from phonenumbers import format_number, PhoneNumberFormat, parse
from ast import literal_eval

tz = timezone('Europe/Prague')


def map_day(day):
    id =  {
        'Monday': 'pondělí',
        'Tuesday': 'úterý',
        'Wednesday': 'středa',
        'Thursday': 'čtvrtek',
        'Friday': 'pátek',
        'Saturday': 'sobota',
        'Sunday': 'neděle'
    }[day]

    return 'https://data.mvcr.gov.cz/zdroj/číselníky/dny-v-týdnu/položky/%s' % id

def build_place(src, type_matcher, config):

    ret = {
        '@context': 'https://ofn.gov.cz/turistické-cíle/2020-07-01/kontexty/turistický-cíl.jsonld',
        'typ': 'Turistický cíl',
        'iri': src.get('url'),
        'název': {
            'cs': src.get('name')
        },
    }

    mail = src.get('organizer_email')
    if mail:
        ret['kontakt'][0]['email'] = 'mailto:%s' % mail 

    tickets = src.get('tickets')
    if tickets:
        ret['vstupné'] = [{
            'typ': 'Vstupné',
            'podmínka': {
                'cs': tickets,
            },
        }]

    description = src.get('text')
    if description:
        ret['popis'] = {
            'cs': description
        }

    image = src.get('image')

    if image:
        ext = "."+ image.split("/")[-1:][0].split(".")[-1:][0]
        ret['příloha'] = [{
            'typ': 'Digitální objekt',
            'url': image,
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

    contact_email = src.get('contact_email')
    contact_phone = src.get('contact_phone')
    contact_website = src.get('contact_website')

    if contact_email or contact_phone or contact_website:
        ret['kontakt'] = [{
            'typ': 'Kontakt'
        }]

    if contact_email:
        ret['kontakt'][0]['email'] = 'mailto:%s' % contact_email

    if contact_website:
        ret['kontakt'][0]['url'] = contact_website

    if contact_phone:
        try:
            phone = parse(contact_phone)
            ret['kontakt'][0]['telefon'] = format_number(phone, PhoneNumberFormat.RFC3966)
        except Exception as e:
            pass


    opening_hours = src.get('opening_hours')
    if opening_hours:
        try:
            hours = literal_eval(opening_hours)
            available_days = set(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
            openings = {}

            # make sure possible dayOfWeek=None is last
            hours = sorted(hours, key=lambda item: item['dayOfWeek'] or '_')

            for h in hours:
                day = h.get('dayOfWeek')
                opens = h.get('opens')
                closes = h.get('closes')

                if opens and closes:
                    openings.setdefault((opens, closes), [])
                    openings[(opens, closes)].append(day)
                    available_days.remove(day)


            ret['otevírací_doba'] = []

            for opening_hours, opening_days in openings.items():
                segment = {
                    'typ': 'Časová specifikace',
                    'časová_doba': [{
                        'typ': 'Časová doba',
                        'od': opening_hours[0] + ':00',
                        'do': opening_hours[1] + ':00'
                    }],
                    'den_v_týdnu': []
                }

                for day in opening_days:
                    if day is not None:
                        segment['den_v_týdnu'].append(map_day(day))
                    else:
                        for d in available_days:
                            segment['den_v_týdnu'].append(map_day(d))

                ret['otevírací_doba'].append(segment)

        except Exception as e:
            pass


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


