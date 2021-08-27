#!/usr/bin/env python3

import requests
import click
from rdflib import Graph, Namespace
from rdflib.namespace import DCAT, RDF

DCT = Namespace("http://purl.org/dc/terms/")

@click.command()
@click.argument('url')
def check(url):
    """Simple tool to check response codes for all presented datasets"""

    index = requests.get(url)

    graph = Graph()
    graph.parse(data=index.text, format='ttl')

    for url in graph.objects(predicate=DCAT.dataset):
        res = requests.get(url)
        click.secho('[', nl=False)
        color = 'green' if res.status_code == 200 else 'red'
        click.secho(str(res.status_code), nl=False, fg=color)
        click.secho('] ', nl=False)
        click.secho(url)

if __name__ == '__main__':
    check()
