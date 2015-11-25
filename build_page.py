# -*- coding: utf-8 -*-
import os
import codecs
import argparse
from json import load
from datetime import date, timedelta, datetime

import ashes
from boltons.fileutils import mkdir_p

from common import (HTML_PATH_TMPL,
                    HTML_FILE_TMPL,
                    DATA_PATH_TMPL,
                    DEFAULT_LANG,
                    DEFAULT_PROJECT)


DEFAULT_TEMPALTE_NAME = 'chart.dust'


def check_issue(cur_date, days, lang, project):
    query_date = cur_date - timedelta(days=days)
    filename = HTML_PATH_TMPL.format(lang=lang,
                                     project=project,
                                     year=query_date.year,
                                     month=query_date.month,
                                     day=query_date.day)
    if os.path.isfile(filename):
        return HTML_FILE_TMPL.format(lang=lang,
                                     project=project,
                                     year=query_date.year,
                                     month=query_date.month,
                                     day=query_date.day)
    return None


def save_issue(query_date, lang, project):
    date_str = query_date.strftime('%Y%m%d')
    file_name = DATA_PATH_TMPL.format(lang=lang,
                                      project=project,
                                      year=query_date.year,
                                      month=query_date.month,
                                      day=query_date.day)
    with codecs.open(file_name, 'r') as data_file:
        data = load(data_file)
    ashes_env = ashes.AshesEnv(['./templates'], keep_whitespace=True)
    data['prev'] = check_issue(query_date, 1, lang, project)
    data['next'] = check_issue(query_date, -1, lang, project)
    rendered = ashes_env.render(DEFAULT_TEMPALTE_NAME, data)
    outfile_name = HTML_PATH_TMPL.format(lang=lang,
                                         project=project,
                                         year=query_date.year,
                                         month=query_date.month,
                                         day=query_date.day)
    try:
        out_file = codecs.open(outfile_name, 'w', 'utf-8')
    except IOError:
        mkdir_p(os.path.dirname(outfile_name))
        out_file = codecs.open(outfile_name, 'w', 'utf-8')
    with out_file:
        out_file.write(rendered)
    print 'successfully generated %s' % outfile_name


def save_and_update(cur_date, lang, project):
    save_issue(cur_date, lang, project)
    if check_issue(cur_date, 1, lang, project):
        prev_date = cur_date - timedelta(days=1)
        save_issue(cur_date, lang, project)
    if check_issue(cur_date, -1, lang, project):
        next_date = cur_date + timedelta(days=1)
        save_issue(next_date, lang, project)
    return 'Saved and updated'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date')
    parser.add_argument('--lang', default=DEFAULT_LANG)
    parser.add_argument('--project', default=DEFAULT_PROJECT)
    args = parser.parse_args()
    if not args.date:
        input_date = date.today() - timedelta(days=1)
    else:
        input_date = datetime.strptime(args.date, '%Y%m%d')
    print save_and_update(input_date, args.lang, args.project)
