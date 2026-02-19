#-*- coding:utf-8 -*-

import re, time

from twisted.internet.protocol import ReconnectingClientFactory
from twisted.python import log
from sys import stderr
from twisted.python.log import startLogging
startLogging(stderr)
from twisted.words.protocols.irc import IRCClient
from werkzeug.urls import url_quote_plus
import os.path

from vlasisku import database
from vlasisku.utils import jbofihe, jvocuhadju, compound2affixes


class BotBase(IRCClient):

    def signedOn(self):
        log.msg('* Logged on')
        self.factory.resetDelay()

        try:
            if self.nickname != self.registered_nickname:
                log.msg('In signedOn: Ghosting with NickServ.')
                self.msg('NickServ', 'GHOST %s %s' % (self.registered_nickname, self.factory.load_password()))
                time.sleep(1)

                log.msg('In signedOn: Setting to proper nickname.')
                self.setNick(self.registered_nickname)
                time.sleep(1)

            log.msg('In signedOn: Identifying with NickServ.')
            self.msg('NickServ', 'IDENTIFY %s' % self.factory.load_password().strip())
            time.sleep(1)
        except AttributeError:
            pass # not registered

        time.sleep(3)

        for c in self.factory.channels:
            log.msg('In signedOn: Joining %s' % c)
            self.join(c)

    def userQuit(self, user, quitMessage):
        try:
            if user == self.registered_nickname:
                self.setNick(self.registered_nickname)
        except AttributeError:
            pass # not registered
    
    def nickChanged(self, nick):
        self.nickname = nick
        try:
            if nick == self.registered_nickname:
                log.msg('In nickChanged: Identifying with NickServ.')
                self.msg('NickServ', 'IDENTIFY %s' % self.factory.load_password().strip())
                time.sleep(2)
        except AttributeError:
            pass # not registered

    # The inherited implementation passes notices to privmsg, causing upset.
    def noticed(self, user, channel, message):
        if channel == self.nickname:
            log.msg('In noticed: -%s- %s' % (user, str(type(message)) + message))
            # Here we do a crappy job of handling the whole "wait for nickserv
            # to do our stuff" thing, now that we have to be registered to join
            # #lojban
            if re.match(r'NickServ', user):
                # Keep trying to identify until it says we have
                if 'has been ghosted' in message:
                    log.msg('In noticed: Finished ghosting; setting to proper nickname.')
                    self.setNick(self.registered_nickname)
                    time.sleep(1)
                    return
                elif 'This nickname is registered' in message:
                    log.msg('In noticed: Identifying with NickServ.')
                    self.msg('NickServ', 'IDENTIFY %s' % self.factory.load_password().strip())
                    time.sleep(2)
                elif 'is not a registered nickname' in message:
                    log.msg('In noticed: Ghosting with NickServ.')
                    self.msg('NickServ', 'GHOST %s %s' % (self.registered_nickname, self.factory.load_password()))
                    time.sleep(1)

                    log.msg('In noticed: Setting to proper nickname.')
                    self.setNick(self.registered_nickname)
                    time.sleep(1)
                    return
                elif 'You are already logged in' in message or 'You are now identified for' in message:
                    # And when we're done, join channels
                    for c in self.factory.channels:
                        log.msg('In noticed: Joining %s' % c)
                        self.join(c)
                        time.sleep(2)
                else:
                    log.msg('In noticed: UNKNOWN NickServ MESSAGE, trying some stuff.')
                    if self.nickname != self.registered_nickname:
                        log.msg('In noticed: Ghosting with NickServ.')
                        self.msg('NickServ', 'GHOST %s %s' % (self.registered_nickname, self.factory.load_password()))
                        time.sleep(1)

                    log.msg('In noticed: Identifying with NickServ.')
                    self.msg('NickServ', 'IDENTIFY %s' % self.factory.load_password().strip())
                    time.sleep(2)

    def msg(self, target, message):
        log.msg('<%(nickname)s> %(message)s' %
            dict(nickname=self.nickname, message=message))
        IRCClient.msg(self, target, message)

    def privmsg(self, user, channel, message):
        nick = user[:user.index('!')]

        # PM?
        if channel == self.nickname:
            target = nick
            private = True
        else:
            target = channel
            private = False

        query = None
        if target != channel:
            query = message
        else:
            trigger = r'^(?:<\S+>: )?%(nickname)s[:,]? (?P<query>.+)' \
                    % dict(nickname=re.escape(self.nickname))
            match = re.match(trigger, message)
            if match:
                query = match.group('query')

        if query:
            log.msg('<%(nick)s> %(message)s' % locals())
            self.query(target, query, private)

class FactoryBase(ReconnectingClientFactory):
    server = 'irc.lojban.org'
    port = 6667
    channels = ['#lojban', '#ckule', '#balningau', '#vlalinkei']

    def __init__(self, app):
        self.app = app
    
    def load_password(self):
        with open(os.path.join(self.app.root_path, 'data/irc.nickserv.%s.secret' % self.protocol.registered_nickname), 'r') as f:
            return f.read()


class WordBot(BotBase):

    nickname = 'valsi'
    registered_nickname = 'valsi'

    def query(self, target, query, private):
        fields = 'affix|class|type|notes|cll|url|components|lujvo'

        if query == 'help!':
            self.msg(target, '<query http://tiny.cc/query-format > '
                             '[(%s)]' % fields)
            return
        elif query == 'update!':
            def do_update():
                from contextlib import closing
                import urllib.request
                import xml.etree.cElementTree as etree
                import os

                self.msg(target, 'downloading...')
                opener = urllib.request.build_opener()
                opener.addheaders = [('User-Agent', 'vlasisku')]
                url = 'https://lensisku.lojban.org/api/export/cached/en/xml'
                with closing(opener.open(url)) as data:
                    xml = etree.parse(data)
                    assert xml.getroot().tag == 'dictionary'
                    with open('vlasisku/data/lensisku.xml', 'w') as file:
                        xml.write(file, 'utf-8')
                self.msg(target, 'updating...')
                database.init_app(database.app, True)
                self.msg(target, 'done!')

            import threading
            threading.Thread(target=do_update).start()
            return

        field = 'definition'
        match = re.search(r'\s\((?P<field>%s)\)$' % fields, query)
        if match:
            field = match.group('field')
            query = re.sub(r'\s\(.+?\)$', '', query)

        if field == 'lujvo':
            try:
                lujvos = jvocuhadju(query)
                tanru = query
                query = lujvos[0]
            except ValueError as e:
                self.msg(target, 'error: %s' % e)
                return

        url = 'http://%s/%s' % (self.factory.app.config['WEBSITE'], url_quote_plus(query))
        results = database.root.query(query)

        entry = results['entry']
        if not entry and len(results['matches']) == 1:
            entry = results['matches'].pop()

        if entry or field in ['components', 'lujvo']:
            case = lambda x: field == x
            if case('definition'):
                data = entry.textdefinition
            elif case('affix'):
                data = ', '.join('-%s-' % i for i in entry.affixes)
            elif case('class'):
                data = entry.grammarclass
            elif case('type'):
                data = entry.type
            elif case('notes'):
                data = entry.textnotes
            elif case('cll'):
                data = '  '.join(link for (chap, link) in entry.cll)
            elif case('url'):
                data = url
            elif case('components'):
                entry = query
                data = ' '.join(e.word for a in compound2affixes(query)
                                if len(a) != 1
                                for e in database.root.entries.values()
                                if a in e.searchaffixes)
            elif case('lujvo'):
                data = ', '.join(lujvos)
                if entry:
                    data += ' (defined as %s = %s)' % (query, entry.textdefinition.encode('utf-8'))
                entry = tanru

            data = data or '(none)'
            if field == 'definition':
                format = '%s = %s'
                self.msg(target, format % (entry, data))
            else:
                format = '%s (%s) = %s'
                self.msg(target, format % (entry, field, data))

        elif results['matches']:
            format = '%d result%s: %s'
            matches = (results['words']
                      +results['glosses']
                      +results['affix']
                      +results['classes']
                      +results['types']
                      +results['definitions']
                      +results['notes'])
            if private:
                data = ', '.join(map(str, matches))
            else:
                data = ', '.join(map(str, matches[:10]))
                if len(results['matches']) > 10:
                    data += '…'
            self.msg(target, format % (len(results['matches']),
                                       's' if len(results['matches']) != 1
                                           else '',
                                       data))
        else:
            if field not in ['components', 'lujvo']:
                rafsi = compound2affixes(query)
                try:
                    if len(rafsi) > 0:
                        tanru = [e.word for a in rafsi
                                        if len(a) != 1
                                        for e in database.root.entries.values()
                                        if a in e.searchaffixes]
                        lujvo = jvocuhadju(' '.join(tanru))[0]
                        if lujvo != query:
                            if field != 'definition':
                                return self.query(target, '%s (%s)' % (lujvo, field), private)
                            else:
                                return self.query(target, lujvo, private)
                except:
                    pass
            self.msg(target, 'no results. %s' % url)

class WordBotFactory(FactoryBase):
    protocol = WordBot


class GrammarBot(BotBase):

    nickname = 'gerna'
    registered_nickname = 'gerna'

    def query(self, target, query, private):
        try:
            response = jbofihe(query)
        except ValueError as e:
            response = str(e)

        self.msg(target, response)

class GrammarBotFactory(FactoryBase):
    protocol = GrammarBot
