#-*- coding:utf-8 -*-

from __future__ import with_statement

from collections import defaultdict
import re
from functools import wraps
from contextlib import contextmanager
from subprocess import Popen, PIPE
from threading import Thread
from Queue import Queue
import os
import signal

from pqs import Parser
from flask import current_app, request
import jellyfish
import jellyfish._jellyfish as py_jellyfish


def parse_query(query):
    """Parse a search query into a dict mapping fields to lists of match tests.

    >>> parse_query('word:coi')['word']
    ['coi']
    >>> parse_query('coi rodo')['all']
    ['coi', 'rodo']
    >>> parse_query('anythingrandom:foo')['anythingrandom']
    ['foo']
    """
    parsed = defaultdict(list)
    parser = Parser()
    parser.quotechars = set([('"', '"')])
    query = re.sub(r'(\w+?):"', r'"\1:', query)
    for _, token in parser.parse(query):
        if ':' in token:
            field, match = token.split(':', 1)
        else:
            field, match = 'all', token
        parsed[field].append(match)
    return parsed


def unique(iterable):
    """Generator that yields each item only once, in the input order.

    >>> list(unique([1,1,2,2,3,3,2,2,1,1]))
    [1, 2, 3]
    >>> list(unique([3,1,3,2,1,3,2]))
    [3, 1, 2]
    >>> ''.join(unique('A unique string? That does not make much sense!'))
    'A uniqestrg?Thadomkc!'
    """
    seen = set()
    for item in iterable:
        if item not in seen:
            seen.add(item)
            yield item


def compound2affixes(compound):
    """Split a compound word into affixes and glue."""
    c = r'[bcdfgjklmnprstvxz]'
    v = r'[aeiou]'
    cc = r'''(?:bl|br|
                cf|ck|cl|cm|cn|cp|cr|ct|
                dj|dr|dz|fl|fr|gl|gr|
                jb|jd|jg|jm|jv|kl|kr|
                ml|mr|pl|pr|
                sf|sk|sl|sm|sn|sp|sr|st|
                tc|tr|ts|vl|vr|xl|xr|
                zb|zd|zg|zm|zv)'''
    vv = r'(?:ai|ei|oi|au)'
    rafsi3v = r"(?:%(cc)s%(v)s|%(c)s%(vv)s|%(c)s%(v)s'%(v)s)" % locals()
    rafsi3 = r'(?:%(rafsi3v)s|%(c)s%(v)s%(c)s)' % locals()
    rafsi4 = r'(?:%(c)s%(v)s%(c)s%(c)s|%(cc)s%(v)s%(c)s)' % locals()
    rafsi5 = r'%(rafsi4)s%(v)s' % locals()

    for i in xrange(1, len(compound)/3+1):
        reg = r'(?:(%(rafsi3)s)([nry])??|(%(rafsi4)s)(y))' % locals() * i
        reg2 = r'^%(reg)s(%(rafsi3v)s|%(rafsi5)s)$$' % locals()
        matches = re.findall(reg2, compound, re.VERBOSE)
        if matches:
            return [r for r in matches[0] if r]

    return []




def etag(f):
    """Decorator to add ETag handling to a callback."""
    @wraps(f)
    def wrapper(**kwargs):
        if request.if_none_match.contains(current_app.config['ETAG']):
            return current_app.response_class(status=304)
        response = current_app.make_response(f(**kwargs))
        response.set_etag(current_app.config['ETAG'])
        return response
    return wrapper


@contextmanager
def ignore(exc):
    """Context manager to ignore an exception."""
    try:
        yield
    except exc:
        pass


def dameraulevenshtein(seq1, seq2):
    """Calculate the Damerau-Levenshtein distance between sequences.

    This distance is the number of operations (consisting of insertions,
    deletions or substitutions of a single character, or transposition of two
    adjacent characters) required to change one sequence into the other.

    Arguments may be str or unicode.

    >>> dameraulevenshtein('ba', 'abc')
    2
    >>> dameraulevenshtein('fee', 'deed')
    2
    >>> dameraulevenshtein(u'abcd', u'bacde')
    2
    >>> dameraulevenshtein(u'number e', u'number \u03c0')
    1
    """
    if isinstance(seq1, str):
        seq1 = unicode(seq1, 'utf-8')
    if isinstance(seq2, str):
        seq2 = unicode(seq2, 'utf-8')

    # Fall back onto Python implementation for code points unsupported by the C
    # implementation.
    # https://github.com/jamesturk/jellyfish/issues/55#issuecomment-312509263
    try:
        return jellyfish.damerau_levenshtein_distance(seq1, seq2)
    except ValueError:
        return py_jellyfish.damerau_levenshtein_distance(seq1, seq2)


def jbofihe(text):
    """Call ``jbofihe -ie -cr'' on text and return the output.

    >>> jbofihe('coi rodo')
    "(0[{coi <(1ro BOI)1 do> DO'U} {}])0"
    >>> jbofihe('coi ho')
    Traceback (most recent call last):
      ...
    ValueError: not grammatical: coi _ho_ ⚠
    >>> jbofihe("coi ro do'u")
    Traceback (most recent call last):
      ...
    ValueError: not grammatical: coi ro _do'u_ ⚠
    >>> jbofihe('coi ro')
    Traceback (most recent call last):
      ...
    ValueError: not grammatical
    >>> jbofihe('(')
    Traceback (most recent call last):
      ...
    ValueError: parser timeout
    """
    data = Queue(1)
    process = Popen(('jbofihe', '-ie', '-cr'),
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)

    def target(queue):
        queue.put(process.communicate(text))

    thread = Thread(target=target, args=(data,))
    thread.start()
    thread.join(1)

    if thread.isAlive():
        os.kill(process.pid, signal.SIGTERM)
        raise ValueError('parser timeout')

    output, error = data.get()
    grammatical = not process.returncode # 0=grammatical, 1=ungrammatical

    if grammatical:
        return output.replace('\n', ' ').rstrip()

    error = error.replace('\n', ' ')
    match = re.match(r"^Unrecognizable word '(?P<word>.+?)' "
                     r"at line \d+ column (?P<column>\d+)", error)
    if match:
        reg = r'^(%s)(%s)(.*)' % ('.' * (int(match.group('column')) - 1),
                                  re.escape(match.group('word')))
        text = re.sub(reg, r'\1_\2_ ⚠ \3', text).rstrip()
        raise ValueError('not grammatical: %s' % text)

    if '<End of text>' in error:
        raise ValueError('not grammatical: %s ⚠' % text)

    match = re.search(r'Misparsed token :\s+(?P<word>.+?) \[.+?\] '
                      r'\(line \d+, col (?P<column>\d+)\)', error)
    if match:
        reg = r'^(%s)(%s)(.*)' % ('.' * (int(match.group('column')) - 1),
                                   match.group('word'))
        text = re.sub(reg, r'\1_\2_ ⚠ \3', text).rstrip()
        raise ValueError('not grammatical: %s' % text)

    raise ValueError('not grammatical')

def jvocuhadju(text):
    """Call ``jvocuhadju'' on text and return the output.
    Returns up to 4 highest-scoring lujvo as a list of strings, ascending order by score.

    >>> jvocuhadju('melbi cmalu nixli ckule')
    ["mlecmaxlicu'e", "melcmaxlicu'e", "mlecmanixycu'e", "melcmanixycu'e"]
    >>> jvocuhadju('coi rodo')
    Traceback (most recent call last):
      ...
    ValueError: Cannot use component [coi] in forming lujvo.
    """
    data = Queue(1)
    process = Popen(('/usr/local/bin/jvocuhadju',) + tuple(text.split(' ')),
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)

    def target(queue):
        queue.put(process.communicate(''))

    thread = Thread(target=target, args=(data,))
    thread.start()
    thread.join(1)

    if thread.isAlive():
        os.kill(process.pid, signal.SIGTERM)
        raise ValueError('jvocuhadju timeout')

    output, error = data.get()

    if len(output) == 0:
        raise ValueError(error.replace('\n', '. ').rstrip())

    output = output.split('\n')
    lujvo_started = 0
    lujvo = []
    for line in output:
        if len(line) > 0:
            if line[0] == '-':
                lujvo_started += 1
                continue
            if lujvo_started == 2:
                cols = line.split(' ')
                lujvo.append(cols[-1])
    return lujvo

