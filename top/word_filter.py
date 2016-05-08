# -*- coding: utf-8 -*-
WORD_FILTERS = ['penis',
                'sex',
                'masturbat',
                'missionary',
                'Luxurieux',
                'xxx',
                'fellatio',
                'reproductive',
                'brust',
                'Kamasutra',
                'Condom',
                'Klimt',
                'XHamster',
                u'بارت',
                u'آمیزش',
                u'فرج',
                u'مقعد',
                u'پورنوگرافی',
                u'جنسی',
                u'مهبل',
                u'اوشن']


def word_filter(text):
    words = text.replace('_', ' ').replace('-', ' ').split()
    for word in words:
        for word_filter in WORD_FILTERS:
            if word_filter.lower() in word.lower():
                #print ' -> filtering:', word, 'from', text
                return True
    return False


if __name__ == '__main__':
    import pdb
    pdb.set_trace()
