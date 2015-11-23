# -*- coding: utf-8 -*-
import os
import codecs
import argparse

import json
import ashes
from boltons.fileutils import mkdir_p
from common import HTML_PATH_TMPL

DEFAULT_TEMPALTE_NAME = 'chart.dust'


def save(file_name):
    with codecs.open(file_name, 'r') as data_file:
        data = json.load(data_file)
    ashes_env = ashes.AshesEnv(['./templates'], keep_whitespace=True)
    rendered = ashes_env.render(DEFAULT_TEMPALTE_NAME, data)
    date_str = '%s%s%s' % (data['date']['year'],
                           data['date']['month'],
                           data['date']['day'])
    outfile_name = HTML_PATH_TMPL.format(lang=data['lang'],
                                         project=data['project'],
                                         date=date_str)
    try:
        out_file = codecs.open(outfile_name, 'w', 'utf-8')
    except IOError:
        mkdir_p(os.path.dirname(outfile_name))
        out_file = codecs.open(outfile_name, 'w', 'utf-8')
    with out_file:
        out_file.write(rendered)
    print 'successfully generated %s' % outfile_name


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file_name', help='input JSON')
    args = parser.parse_args()
    save(args.file_name)
