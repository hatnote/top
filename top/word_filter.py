# -*- coding: utf-8 -*-
import unwelcome_files as unwelcome

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
                'hustler',
                'Sharka',
                'ejaculat',
                'vagina',
                u'ਯੋਨੀ',
                u'پستان',
                u'بارت',
                u'آمیزش',
                u'فرج',
                u'مقعد',
                u'پورنوگرافی',
                u'جنسی',
                u'مهبل',
                u'اوشن']


def word_filter(text):
    text = text.replace('_', ' ').replace('File:', '')
    if text in unwelcome.file_names:
        return True

    words = text.replace('-', ' ').split()
    for word in words:
        for word_filter in WORD_FILTERS:
            if word_filter.lower() in word.lower():
                #print ' -> filtering:', word, 'from', text
                return True
    return False


if __name__ == '__main__':
    import pdb
    pdb.set_trace()
