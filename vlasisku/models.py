from vlasisku.utils import compound2affixes


class Entry(object):
    """Container for lensisku entry data."""

    #: The word (or compound) this entry describes.
    word = None

    #: The type of the word, such as ``'gismu'``.
    type = None

    #: A list of three-letter affix forms for the word.
    affixes = None

    #: A list of affixes including four and five-letter versions.
    searchaffixes = None

    #: The grammatical class if the word is a particle.
    grammarclass = None

    #: The grammatical class of this words terminator, if any.
    terminator = None

    #: A list of grammatical classes this word terminates, for terminators.
    terminates = None

    #: A list of two-tuples such as ``('<chapter>.<section>', 'http://...')``.
    cll = None

    #: HTML for the entry definition, such as a place structure.
    definition = None

    #: HTML for notes about the entry.
    notes = None

    #: Plain text definition.
    textdefinition = None

    #: Plain text notes.
    textnotes = None

    #: The :class:`~vlasisku.database.Root` instance this entry is in.
    db = None

    # We need new lists for every instance.
    def __init__(self, db):
        self.affixes = []
        self.searchaffixes = []
        self.terminates = []
        self.cll = []
        self.db = db

    def __str__(self):
        return self.word

    def __repr__(self):
        return '<Entry %s>' % self.word

    def components(self):
        """Build HTML that links the affixes in a compound
        to their corresponding words, with definitions in the link tooltips.

        """
        if self.type == 'lujvo':
            components = ''
            for a in compound2affixes(self.word):
                if len(a) == 1:
                    components += a
                else:
                    word = [e for e in self.db.entries.values()
                              if a in e.searchaffixes]
                    if word:
                        components += '<a href="%s" ' % word[0]
                        components += 'title="<strong>%s:</strong> ' % word[0]
                        components += '%s">%s</a>' % (word[0].definition, a)
                    else:
                        components += a
            return components


class Gloss(object):
    """Container for lensisku gloss data."""

    #: The actual gloss word.
    gloss = None

    #: The :class:`Entry` this glosses to.
    entry = None

    #: The sense in which this gloss word relates to the entry, or ``None``.
    sense = None

    #: The specific place of the entry this glosses to, if any.
    place = None

    def __str__(self):
        return self.entry.word
