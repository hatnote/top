
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
                'Klimt']


def word_filter(text):
    words = text.replace('_', ' ').replace('-', ' ').split()
    for word in words:
        for word_filter in WORD_FILTERS:
            if word_filter.lower() in word.lower():
                return True
    return False


if __name__ == '__main__':
    import pdb
    pdb.set_trace()
