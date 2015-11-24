# -*- coding: utf-8 -*-
import os
import codecs
import argparse
from json import load
from datetime import date, timedelta, datetime

import ashes
from boltons.fileutils import mkdir_p

from common import HTML_PATH_TMPL


DEFAULT_TEMPALTE_NAME = 'chart.dust'


def check_issue(date_str, days, lang, project):
    cur_date = datetime.strptime(date_str, '%Y%m%d')
    query_date = cur_date - timedelta(days=days)
    filename = HTML_PATH_TMPL.format(lang=lang,
                                     project=project,
                                     date=query_date.strftime('%Y%m%d'))
    return os.path.isfile(filename)


def save(file_name):
    with codecs.open(file_name, 'r') as data_file:
        data = load(data_file)
    ashes_env = ashes.AshesEnv(['./templates'], keep_whitespace=True)
    date_str = '%s%s%s' % (data['date']['year'],
                           data['date']['month'],
                           data['date']['day'])
    lang = data['lang']
    project = data['project']
    data['prev'] = check_issue(date_str, 1, lang, project)
    data['next'] = check_issue(date_str, -1, lang, project)
    rendered = ashes_env.render(DEFAULT_TEMPALTE_NAME, data)
    outfile_name = HTML_PATH_TMPL.format(lang=lang,
                                         project=project,
                                         date=date_str)
    print (data['prev'], data['next'])
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
