#-*- coding:utf-8 -*-

from nose.tools import istest as test, \
                       assert_equal as same, \
                       assert_not_equal as differ

from vlasisku import app
from vlasisku.extensions import database
from vlasisku.utils import compound2affixes, parse_query
from vlasisku.database import tex2html, braces2links


app.debug = False
client = app.test_client()


def something(value):
    assert value is not None, '%s is None' % value

def nothing(value):
    assert value is None, '%s is not None' % value


@test
def sets_etag():
    """Sets an ETag header for index and query pages"""
    something(client.get('/').get_etag()[0])
    something(client.get('/coi').get_etag()[0])

@test
def sensitive_to_if_none_match_header():
    """Sends a 304 if ETags match"""
    index = client.get('/', headers={'If-None-Match': app.config['ETAG']})
    query = client.get('/coi', headers={'If-None-Match': app.config['ETAG']})
    same(index.status_code, 304)
    same(query.status_code, 304)


@test
def compound2affixes_splits_compounds():
    """The compound2affixes util splits compounds into affixes"""
    same(compound2affixes('jbobau'), ['jbo', 'bau'])
    same(compound2affixes('lobybau'), ['lob', 'y', 'bau'])
    same(compound2affixes('jbobangu'), ['jbo', 'bangu'])
    same(compound2affixes('lojbybau'), ['lojb', 'y', 'bau'])
    same(compound2affixes('lobybangu'), ['lob', 'y', 'bangu'])
    same(compound2affixes('lojbybangu'), ['lojb', 'y', 'bangu'])
    same(compound2affixes("ro'inre'o"), ["ro'i", 'n', "re'o"])

@test
def tex2html_does_math():
    """The tex2html util handles basic math"""
    same(tex2html('$x_1$'), 'x<sub>1</sub>')
    same(tex2html('$10^2$'), '10<sup>2</sup>')
    same(tex2html('$1*10$'), u'1×10')

@test
def tex2html_does_typography():
    """The tex2html util handles basic typography"""
    same(tex2html(r'\emph{coi}'), '<em>coi</em>')
    same(tex2html(r'\textbf{coi}'), '<strong>coi</strong>')

@test
def braces2links_does_known_words():
    """The braces2links util handles known words"""
    same(braces2links('{coi}', database.root.entries),
         '<a href="coi" title="vocative: greetings/hello.">coi</a>')

@test
def braces2links_does_unknown_words():
    """The braces2links util links lensisku for unknown words"""
    same(braces2links('{unknown}', database.root.entries),
         '<a href='
         '"https://lensisku.lojban.org/en/valsi/unknown" '
         'title="This word is missing, please add it!" class="missing">'
         'unknown</a>')

@test
def parse_query_splits_queries():
    """The parse_query util links fields to lists of tokens"""
    same(parse_query('class:BAI event affix:bau'),
         {'class': ['BAI'], 'all': ['event'], 'affix': ['bau']})
