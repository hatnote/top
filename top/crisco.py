# -*- coding: utf-8 -*-
"""Crisco because this module does shortening. Sentence-oriented
shortening, currently only for English.
"""

from __future__ import unicode_literals

import re

caps = "([A-Z])"
prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = ("(Mr|Mrs|Ms|Dr|He\s|She\s|It\s|They\s"
            "|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)")
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov)"


DEFAULT_MAX_LEN = 400
DEFAULT_MIN_SENT = 1
SHORTEN_FUNC_MAP = {}  # initialized below


def shorten(text, lang, max_len=DEFAULT_MAX_LEN, min_sent=DEFAULT_MIN_SENT):
    """Shorten `text` by sentence, taking into account language `lang`,
    maximum desired length (`max_len`), and a minimum number of sentences
    (`min_sent`).
    """
    shorten_func = SHORTEN_FUNC_MAP.get(lang, default_shorten)
    return shorten_func(text, max_len=max_len)


def default_shorten(text, max_len=DEFAULT_MAX_LEN, min_count=DEFAULT_MIN_SENT):
    return text


def en_shorten(text, max_len=DEFAULT_MAX_LEN, min_count=DEFAULT_MIN_SENT):
    if not text:
        return text
    ret_sentences = []
    sentences = en_split_sentences(text)
    cur_len = 0
    for sentence in sentences:
        if (len(ret_sentences) < min_count
            or (cur_len + len(sentence) + 1) < max_len):
            cur_len += len(sentence)
            ret_sentences.append(sentence)
        else:
            break
    return ' '.join(ret_sentences)


def en_split_sentences(text):
    # from http://stackoverflow.com/questions/4576077/python-split-text-on-sentences
    # it's not pretty, don't read this
    text = " " + text + "  "
    text = text.replace("\n", " ")
    text = re.sub(prefixes,"\\1<prd>", text)
    text = re.sub(websites,"<prd>\\1", text)
    if "Ph.D" in text: text = text.replace("Ph.D.", "Ph<prd>D<prd>")
    text = re.sub("\s" + caps + "[.] "," \\1<prd> ", text)
    text = re.sub(acronyms+" "+starters,"\\1<stop> \\2", text)
    text = re.sub(caps + "[.]" + caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>\\3<prd>", text)
    text = re.sub(caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>", text)
    text = re.sub(" "+suffixes+"[.] "+starters," \\1<stop> \\2", text)
    text = re.sub(" "+suffixes+"[.]"," \\1<prd>", text)
    text = re.sub(" " + caps + "[.]"," \\1<prd>", text)
    if "”" in text:
        text = text.replace(".”", "”.")
    if "\"" in text:
        text = text.replace(".\"", "\".")
    if "!" in text:
        text = text.replace("!\"", "\"!")
    if "?" in text:
        text = text.replace("?\"", "\"?")
    text = text.replace(".", ".<stop>")
    text = text.replace("?", "?<stop>")
    text = text.replace("!", "!<stop>")
    text = text.replace("<prd>", ".")
    sentences = text.split("<stop>")
    sentences = sentences[:-1]
    sentences = [s.strip() for s in sentences]
    return sentences


SHORTEN_FUNC_MAP['en'] = en_shorten
