
from flask import Flask
import click
from werkzeug.middleware.proxy_fix import ProxyFix

from vlasisku.extensions import database
from vlasisku import components


app = Flask(__name__)
app.debug = True
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)
database.init_app(app)

ETAG = database.etag
from vlasisku.local import *

app.config.from_object(__name__)

app.register_blueprint(components.app)
app.register_blueprint(components.general)
app.register_blueprint(components.opensearch)
app.register_blueprint(components.pages, url_prefix='/page')



@app.cli.command('runbots')
def runbots():
    """Start the IRC bots valsi and gerna."""

    import sys

    from twisted.python import log
    from twisted.internet import reactor

    from vlasisku.irc import GrammarBotFactory, WordBotFactory

    log.startLogging(sys.stdout)

    gerna = GrammarBotFactory(app)
    valsi = WordBotFactory(app)

    reactor.connectTCP(gerna.server, gerna.port, gerna)
    reactor.connectTCP(valsi.server, valsi.port, valsi)
    reactor.run()


@app.shell_context_processor
def shell_context():

    import pprint

    import flask

    import vlasisku

    context = dict(pprint=pprint.pprint)
    context.update(vars(flask))
    context.update(vars(vlasisku))
    context.update(vars(vlasisku.utils))
    context.update(vars(vlasisku.database))
    context.update(vars(vlasisku.models))

    return context

@app.cli.command('updatedb')
def updatedb():
    """Export and index a new database from jbovlaste."""

    from contextlib import closing
    import urllib.request
    import xml.etree.cElementTree as etree
    import os

    print('Downloading jbovlaste xml file; this may take a bit.')

    # Debugging info is nice
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(debuglevel=1))

    # CloudFlare doesn't give out data to urllib2's default user agent
    opener.addheaders = [('User-Agent', 'vlasisku')]

    # The bot key is essentially a magic secret for vlasisku and things like
    # it, so you don't have to login with real credentials.  If it stops
    # working, contact the jbovlaste administrator.
    # Use cached export from lensisku (same jbovlaste format, but faster/stabler).
    url = 'https://lensisku.lojban.org/api/export/cached/en/xml'
    with closing(opener.open(url)) as data:
        print('Parsing jbovlaste xml')
        xml = etree.parse(data)
        assert xml.getroot().tag == 'dictionary'
        print('Storing jbovlaste xml')
        with open('vlasisku/data/jbovlaste.xml', 'wb') as file:
            xml.write(file, 'utf-8')
        print('Removing old database.')
        os.system('''
            rm -f vlasisku/data/db.pickle
            touch vlasisku/database.py
            ''')
    print('The running site should now automatically reload the database, or if it is not running the next startup will do so.')
    # If forcing a reload here is desired, this works: database.init_app(database.app)
