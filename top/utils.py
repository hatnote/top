# -*- coding: utf-8 -*-

import itertools


def grouper(iterable, n):
    '''\
    http://stackoverflow.com/questions/3992735/
        python-generator-that-groups-another-iterable-into-groups-of-n
    '''
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


def shorten_number(num):
    '''\
    http://stackoverflow.com/questions/579310/
        formatting-long-numbers-as-strings-in-python
    '''
    magnitude = 0
    if type(num) is str:
        num = int(num)
        #import pdb; pdb.set_trace()
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    ret = '%.1f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])
    return ret.replace('.0', '')
