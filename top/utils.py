# -*- coding: utf-8 -*-


def shorten_number(num):
    '''\
    http://stackoverflow.com/questions/579310/
        formatting-long-numbers-as-strings-in-python
    '''
    magnitude = 0
    if isinstance(num, str):
        num = int(num)
        #import pdb; pdb.set_trace()
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    ret = '%.1f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])
    return ret.replace('.0', '')
