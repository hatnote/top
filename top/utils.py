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


def int_to_local_str(num, locale=None):
    ret = ''
    if locale == 'fa':
        lnums = [u'۰', u'۱', u'۲', u'۳', u'۴', u'۵', u'۶', u'۷', u'۸',
                 u'۹']
    elif locale == 'ar':
        lnums = [u'٠', u'١', u'٢', u'٣', u'٤', u'٥', u'٦', u'٧', u'٨',
                 u'٩']
    else:
        lnums = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    for char in unicode(num):
        try:
            digit = int(char)
            ret += lnums[digit]
        except ValueError:
            ret += char
            continue
    return ret


if __name__ == '__main__':
    from random import randint
    test = randint(0, 10000)
    print test, int_to_locale_str(test, locale='fa')
    test = 'April 2016'
    print test, int_to_locale_str(test, locale='fa')
    



