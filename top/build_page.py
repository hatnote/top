# -*- coding: utf-8 -*-
import os
import codecs
import argparse
from json import load
from os import listdir
from os.path import join as pjoin, isdir, isfile, dirname
from datetime import date, timedelta, datetime

import ashes
from boltons.fileutils import mkdir_p

from common import (HTML_PATH_TMPL,
                    HTML_FILE_TMPL,
                    DATA_PATH_TMPL,
                    DEFAULT_LANG,
                    BASE_PATH,
                    INDEX_PATH,
                    LANG_INDEX_PATH,
                    PROJECT_INDEX_PATH,
                    LOCAL_LANG_MAP,
                    DEFAULT_PROJECT,
                    ABOUT_PATH,
                    ABOUT)


DEFAULT_TEMPALTE_NAME = 'chart.dust'
ABOUT_TEMPLATE = 'about.dust'

MOST_RECENT_CHART = date.today() - timedelta(days=1)


def save_rendered(outfile_name, template_name, context):
    ashes_env = ashes.AshesEnv(['./top/templates'], keep_whitespace=True)
    rendered = ashes_env.render(template_name, context)
    try:
        out_file = codecs.open(outfile_name, 'w', 'utf-8')
    except IOError:
        mkdir_p(dirname(outfile_name))
        out_file = codecs.open(outfile_name, 'w', 'utf-8')
    with out_file:
        out_file.write(rendered)
    print 'successfully generated %s' % outfile_name


def check_most_recent(lang=DEFAULT_LANG, project=DEFAULT_PROJECT):
    sdir = pjoin(BASE_PATH, lang, project)
    recent_year = max([f for f in listdir(sdir) if isdir(pjoin(sdir, f))])
    sdir = pjoin(sdir, recent_year)
    recent_month = max([f for f in listdir(sdir) if isdir(pjoin(sdir, f))])
    sdir = pjoin(sdir, recent_month)
    recent_day = max([f for f in listdir(sdir) if not f.startswith('.')])
    recent_day = recent_day.replace('.json', '')
    return date(year=int(recent_year),
                month=int(recent_month),
                day=int(recent_day))


def check_projects():
    ret = {}
    for lang in LOCAL_LANG_MAP.keys():
        lang_dir = pjoin(BASE_PATH, lang)
        if isdir(lang_dir):
            projects = [f for f in listdir(lang_dir) if not f.startswith('.')]
            ret[lang] = projects
    return ret


def check_chart(cur_date, days, lang, project):
    query_date = cur_date - timedelta(days=days)
    filename = HTML_PATH_TMPL.format(lang=lang,
                                     project=project,
                                     year=query_date.year,
                                     month=query_date.month,
                                     day=query_date.day)
    if isfile(filename):
        return HTML_FILE_TMPL.format(lang=lang,
                                     project=project,
                                     year=query_date.year,
                                     month=query_date.month,
                                     day=query_date.day)
    return None


def save_chart(query_date, lang, project):
    date_str = query_date.strftime('%Y%m%d')
    file_name = DATA_PATH_TMPL.format(lang=lang,
                                      project=project,
                                      year=query_date.year,
                                      month=query_date.month,
                                      day=query_date.day)
    with codecs.open(file_name, 'r') as data_file:
        data = load(data_file)
    data['current'] = HTML_FILE_TMPL.format(lang=lang,
                                            project=project,
                                            year=query_date.year,
                                            month=query_date.month,
                                            day=query_date.day)
    #TODO: Shouldn't need to format HTML_FILE_TMPL and HTML_PATH_TMPL
    data['prev'] = check_chart(query_date, 1, lang, project)
    data['next'] = check_chart(query_date, -1, lang, project)
    data['about'] = ABOUT
    data['dir_depth'] = '../' * 4
    data['is_index'] = False
    outfile_name = HTML_PATH_TMPL.format(lang=lang,
                                         project=project,
                                         year=query_date.year,
                                         month=query_date.month,
                                         day=query_date.day)
    save_rendered(outfile_name, DEFAULT_TEMPALTE_NAME, data)
    if lang is DEFAULT_LANG and project is DEFAULT_PROJECT:
        data['dir_depth'] = ''
        data['is_index'] = True
        save_rendered(INDEX_PATH, DEFAULT_TEMPALTE_NAME, data)
    if query_date == check_most_recent(lang=lang, project=project):
        # Update language index
        data['dir_depth'] = '../'
        data['is_index'] = True
        lang_index = LANG_INDEX_PATH.format(lang=lang)
        save_rendered(lang_index, DEFAULT_TEMPALTE_NAME, data)
        # Update project index
        data['dir_depth'] = '../../'
        data['is_index'] = True
        project_index = PROJECT_INDEX_PATH.format(lang=lang, project=project)
        save_rendered(project_index, DEFAULT_TEMPALTE_NAME, data)


def update_charts(cur_date, lang, project):
    save_chart(cur_date, lang, project)
    if check_chart(cur_date, 1, lang, project):
        prev_date = cur_date - timedelta(days=1)
        save_chart(cur_date, lang, project)
    if check_chart(cur_date, -1, lang, project):
        next_date = cur_date + timedelta(days=1)
        save_chart(next_date, lang, project)
    return 'Saved and updated'


def update_about():
    project_map = check_projects()
    langs = project_map.keys()
    data = {'languages': [],
            'about': ABOUT}
    for lang in langs:
        lang_name = LOCAL_LANG_MAP[lang]
        data['languages'].append({'name': lang_name,
                                  'url': '%s/index.html' % lang})
    save_rendered(ABOUT_PATH, ABOUT_TEMPLATE, data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date')
    parser.add_argument('--lang', default=DEFAULT_LANG)
    parser.add_argument('--project', default=DEFAULT_PROJECT)
    parser.add_argument('--meta', '-m', action='store_true')
    args = parser.parse_args()
    if args.meta:
        update_about()
    else:
        if not args.date:
            input_date = MOST_RECENT_CHART
        else:
            input_date = datetime.strptime(args.date, '%Y%m%d').date()
        update_charts(input_date, args.lang, args.project)
