from urllib.parse import parse_qs, urlparse

def get_dataset_id(url):
    return parse_qs(urlparse(url).query)['id'][0]