# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unwelcome_files as unwelcome

WORD_FILTERS = ['penis',
                'anal',
                'anus',
                'breast',
                'butt',
                'buttock',
                'blowjob',
                'clitoris',
                'coitus',
                'condom',
                'cunnilingus',
                'defecating',
                'defecate',
                'dildo',
                'sex',
                'urethra',
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
                'pornhub',
                'hustler',
                'Sharka',
                'ejaculat',
                'ejaculation',
                'erect',
                'erected',
                'circumcised',
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
    if not isinstance(text, unicode):
        text = text.decode('utf8')
    text = text.replace('_', ' ').replace('File:', '')
    for file_name in unwelcome.file_names:
        if file_name in text:
            return True

    words = text.replace('-', ' ').split()
    for word in words:
        for filtered_word in WORD_FILTERS:
            if filtered_word.lower() in word.lower():
                #print ' -> filtering:', word, 'from', text
                return True
    return False


if __name__ == '__main__':
    import pdb
    pdb.set_trace()
