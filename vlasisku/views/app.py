
import re

from flask import request, redirect, url_for
from flaskext.genshi import render_response

from vlasisku import app, db
from vlasisku.utils import etag, parse_query, compound2affixes, \
                           dameraulevenshtein
from vlasisku.database import TYPES


@app.route('/')
@etag
def index():
    if 'query' in request.args:
        return redirect(request.args.get('query'))
    types = TYPES
    classes = set(e.grammarclass for e in db.entries.itervalues()
                                 if e.grammarclass)
    scales = db.class_scales
    return render_response('index.html', locals())


@app.route('/<query>')
@etag
def query(query):
    query = query.replace('+', ' ')
    parsed_query = parse_query(query)
    matches = set()
    entry = db.entries.get(query, None)
    if entry:
        matches.add(entry)

    if parsed_query['all']:
        words = []

        glosses = db.matches_gloss(parsed_query['all'], matches)
        matches.update(g.entry for g in glosses)

        affix = db.matches_affix(parsed_query['all'], matches)
        matches.update(affix)

        classes = db.matches_class(parsed_query['all'], matches)
        classes += [e for e in db.entries.itervalues()
                      if e.grammarclass
                      and e not in classes
                      and re.split(r'[0-9*]', e.grammarclass)[0] == query]
        matches.update(classes)

        types = db.matches_type(parsed_query['all'], matches)
        matches.update(types)

        definitions = db.matches_definition(parsed_query['all'], matches)
        matches.update(definitions)

        notes = db.matches_notes(parsed_query['all'], matches)
        matches.update(notes)

    else:
        words = db.matches_word(parsed_query['word'])
        matches.update(words)

        glosses = db.matches_gloss(parsed_query['gloss'], matches)
        matches.update(g.entry for g in glosses)

        affix = db.matches_affix(parsed_query['affix'], matches)
        matches.update(affix)

        classes = db.matches_class(parsed_query['class'], matches)
        matches.update(classes)

        types = db.matches_type(parsed_query['type'], matches)
        matches.update(types)

        definitions = db.matches_definition(parsed_query['definition'], matches)
        matches.update(definitions)

        notes = db.matches_notes(parsed_query['notes'], matches)
        matches.update(notes)

    if parsed_query['word']:
        matches = set(e for e in db.matches_word(parsed_query['word'])
                        if e in matches)
    if parsed_query['gloss']:
        matches = set(g.entry for g in db.matches_gloss(parsed_query['gloss'])
                              if e in matches)
    if parsed_query['affix']:
        matches = set(e for e in db.matches_affix(parsed_query['affix'])
                        if e in matches)
    if parsed_query['class']:
        matches = set(e for e in db.matches_class(parsed_query['class'])
                        if e in matches)
    if parsed_query['type']:
        matches = set(e for e in db.matches_type(parsed_query['type'])
                        if e in matches)
    if parsed_query['definition']:
        matches = set(e for e
                        in db.matches_definition(parsed_query['definition'])
                        if e in matches)
    if parsed_query['notes']:
        matches = set(e for e in db.matches_notes(parsed_query['notes'])
                        if e in matches)

    words = [e for e in words if e in matches]
    glosses = [g for g in glosses if g.entry in matches]
    affix = [e for e in affix if e in matches]
    classes = [e for e in classes if e in matches]
    types = [e for e in types if e in matches]
    definitions = [e for e in definitions if e in matches]
    notes = [e for e in notes if e in matches]

    if not entry and len(matches) == 1:
        return redirect(url_for('query', query=matches.pop()))

    sourcemetaphor = []
    unknownaffixes = None
    similar = None
    if not matches:
        sourcemetaphor = [e for a in compound2affixes(query)
                            if len(a) != 1
                            for e in db.entries.itervalues()
                            if a in e.searchaffixes]

        unknownaffixes = len(sourcemetaphor) != \
                         len([a for a in compound2affixes(query)
                                if len(a) != 1])

        similar = [e.word for e in db.entries.itervalues()
                          if dameraulevenshtein(query, e.word) == 1]

        similar += [g.gloss for g in db.glosses
                            if g.gloss not in similar
                            and dameraulevenshtein(query, g.gloss) == 1]

    return render_response('query.html', locals())


@app.route('/_complete/')
def complete():
    return '\n'.join(db.suggest(request.args.get('q', ''))[1])
