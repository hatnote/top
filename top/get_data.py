# -*- coding: utf-8 -*-
import os
import sys
import time
import json

import codecs
import urllib2
import yaml
from babel.dates import format_date
from itertools import takewhile

from csv import DictReader as csvDictReader
from argparse import ArgumentParser
from urllib import urlencode, quote_plus
from datetime import date, timedelta, datetime

from boltons.fileutils import mkdir_p
from boltons.timeutils import parse_timedelta
from boltons.iterutils import chunked

from utils import shorten_number
from build_page import update_charts
from word_filter import word_filter
from common import (DATA_PATH_TMPL,
                    PERMALINK_TMPL,
                    DATE_PERMALINK_TMPL,
                    TOP_API_URL,
                    MW_API_URL,
                    TOTAL_TRAFFIC_URL,
                    DEBUG,
                    PREFIXES,
                    LOCAL_LANG_MAP,
                    STRINGS_PATH_TMPL,
                    DEFAULT_PROJECT,
                    DEFAULT_LANG)
import crisco
from log import tlog


DEFAULT_LIMIT = 100
DEFAULT_IMAGE = ('https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/'
                 'Wikipedia%27s_W.svg/400px-Wikipedia%27s_W.svg.png')
DEFAULT_SUMMARY = None
DEFAULT_GROUP_SIZE = 20

POLL_INTERVAL = parse_timedelta('10m')


@tlog.wrap('critical')
def get_wiki_info(lang, project):
    '''\
    Get the mainpage title and local namespace map.
    '''
    url = MW_API_URL.format(lang=lang, project=project)
    params = {'action': 'query',
              'meta': 'siteinfo',
              'format': 'json',
              'siprop': 'general|namespaces'}
    resp = urllib2.urlopen(url + urlencode(params))
    data = json.loads(resp.read())
    mainpage = data['query']['general']['mainpage'].replace(' ', '_')
    namespaces = [ns_info['*'].replace(' ', '_') for ns_id, ns_info in
                  data['query']['namespaces'].iteritems() if ns_id is not 0]
    return {'mainpage': mainpage, 'namespaces': namespaces}


def is_article(title, wiki_info):
    '''\
    Is it an article, or some other sort of page? We'll want to filter out the
    search page (Special:Search in English, etc) and similar pages appearing
    inconveniently in the traffic report.

    Skip xhamster. There are a few clues this Wikipedia traffic is artificial.
    See https://en.wikipedia.org/w/index.php?title=XHamster&diff=701682670&oldid=700826198
    '''
    skip = ['-', '404.php', 'XHamster'] + [wiki_info['mainpage']]
    prefixes = PREFIXES + wiki_info['namespaces']
    if title in skip:
        return False
    for prefix in prefixes:
        if title.startswith(prefix + ':'):
            return False
    return True



def get_project_traffic(date, lang, project):
    datestr = date.strftime('%Y%m%d')
    url = TOTAL_TRAFFIC_URL.format(lang=lang, project=project, datestr=datestr)
    resp = urllib2.urlopen(url)
    data = json.loads(resp.read())
    try:
        date_data = data['items'][0]
    except IndexError:
        # backwards compat to the old metrics api which would raise urlerror
        raise urllib2.URLError('no traffic data available from %r' % url)

    return date_data['views']



def get_query(params, lang, project, extractor, default_val):
    '''\
    Generic function for MediaWiki queries.
    '''
    url = MW_API_URL.format(lang=lang, project=project)
    resp = urllib2.urlopen(url + urlencode(params))
    data = json.loads(resp.read())
    ret = {}
    for page_id, page_info in data['query']['pages'].iteritems():
        if int(page_id) < 0:
            ret[page_info['title']] = default_val
        else:
            try:
                ret[page_info['title']] = extractor(page_info)
            except Exception:
                ret[page_info['title']] = default_val
    return ret


@tlog.wrap('debug', inject_as='log_rec')
def get_images(titles, lang, project, log_rec):
    '''\
    Get thumbnails for a group of pages via MediaWiki API.
    '''
    log_rec['count'] = len(titles)
    log_rec['lang'] = lang
    log_rec['project'] = project

    params = {'action': 'query',
              'prop': 'pageimages',
              'pithumbsize': 500,
              'pilicense': 'any',
              'pilimit': 50,
              'format': 'json',
              'titles': '|'.join(titles).encode('utf-8')}
    extractor = lambda page: page.get('thumbnail', {}).get('source',
                                                           DEFAULT_IMAGE)
    images = get_query(params, lang, project, extractor, DEFAULT_IMAGE)

    log_rec.success('finished getting images for {count} {lang}'
                    ' {project} articles')
    return images


@tlog.wrap('debug', inject_as='log_rec')
def get_summaries(titles, lang, project, log_rec):
    '''\
    Get summaries for a group of pages via MediaWiki API.
    '''
    log_rec['count'] = len(titles)
    log_rec['lang'] = lang
    log_rec['project'] = project

    params = {'action': 'query',
              'prop': 'extracts',
              'exsentences': 3,
              'explaintext': 1,
              'exintro': 1,
              'exlimit': 20,
              'format': 'json',
              'titles': '|'.join(titles).encode('utf-8')}
    extractor = lambda page: page['extract']
    summaries = get_query(params, lang, project, extractor, DEFAULT_SUMMARY)

    log_rec.success('finished getting summaries for {count} {lang}'
                    ' {project} articles')
    return summaries


def get_traffic(query_date, lang, project):
    '''\
    Get the traffic report for the top 1000 articles for a given day.
    TODO: Get from local file, if available
    '''
    url = TOP_API_URL.format(lang=lang,
                             project=project,
                             year=query_date.year,
                             month='%02d' % query_date.month,
                             day='%02d' % query_date.day)
    if DEBUG:
        print 'Getting %s' % url
    with tlog.critical('fetch_traffic') as rec:
        resp = urllib2.urlopen(url)
        resp_bytes = resp.read()
        rec.success('Fetched {len_bytes} bytes from {url}',
                    len_bytes=len(resp_bytes), url=url)

    with tlog.critical('deserialize_traffic'):
        data = json.loads(resp_bytes)
        articles = data['items'][0]['articles']
    return articles


@tlog.wrap('debug')
def load_traffic(query_date, lang, project):
    file_name = DATA_PATH_TMPL.format(lang=lang,
                                      project=project,
                                      year=query_date.year,
                                      month=query_date.month,
                                      day=query_date.day)
    try:
        data_file = codecs.open(file_name, 'r')
    except IOError:
        return None
    with data_file:
        return json.load(data_file)


def load_prev_traffic(query_date, limit, lang=DEFAULT_LANG,
                      project=DEFAULT_PROJECT):
    '''\
    Load available local traffic data until we reach the limit.
    '''
    prev_stats = []
    for lookback in range(1, limit):
        prev = query_date - timedelta(days=lookback)
        article_data = load_traffic(prev, lang, project)
        if not article_data:
            break
        prev_stats.append(dict((art['article'], art) for
                               art in article_data['articles']))
    return prev_stats


def find_streaks(title, prev_stats):
    '''\
    Look for streaks in previous data.
    '''
    ranks = [l[title]['rank'] if l.get(title) else None for l in prev_stats]
    history = [l[title]['views'] if l.get(title) else 0 for l in prev_stats]
    history.reverse()
    streak = [a for a in takewhile(lambda r: r, ranks)]
    if len(streak) > 0:
        streak_min = min(ranks)
    else:
        streak_min = None
    if prev_stats > 0 and len(streak) == len(prev_stats):
        streak_len = '%s+' % len(streak)
    else:
        streak_len = len(streak) + 1
    ret = {'streak_len': streak_len,
           'streak_min': streak_min,
           'history': history}
    return ret


def get_tweet_templates(lang):
    strings_path = STRINGS_PATH_TMPL.format(lang=lang)
    try:
        string_file = open(strings_path, 'r')
    except IOError as e:
        default_strings_path = STRINGS_PATH_TMPL.format(lang=DEFAULT_LANG)
        string_file = open(default_strings_path, 'r')
    with string_file:
        strings = yaml.load(string_file)
        tweets = {'long': strings['long_tweet'],
                  'medium': strings['medium_tweet'],
                  'short': strings['short_tweet']}
        return tweets


def tweet_composer(article, lang, project, tweets):
    '''\
    Compose a short tweet for an article based on its stats and a few
    templates.
    '''
    # TODO: load internationalized tweets from the strings YAML
    max_tweet_len = 118  # Plus room for link
    title = article['title']
    project = project.capitalize()
    lang = LOCAL_LANG_MAP[lang]
    if isinstance(article['streak_len'], str):
        streak = article['streak_len'].replace('+', '')
    else:
        streak = article['streak_len']
    if int(streak) > 1:
        msg = tweets['long']
        if not isinstance(msg, unicode):
            msg = msg.decode('utf-8')
        msg = msg.format(streak=article['streak_len'],
                         title=title,
                         rank=article['rank'],
                         project=project,
                         views=article['views_short'])
        if len(msg) < max_tweet_len:
            return msg
    msg = tweets['medium']
    if not isinstance(msg, unicode):
        msg = msg.decode('utf-8')
    try:
        msg = msg.format(title=title,
                         views=article['views_short'],
                         project=project)
    except Exception as e:
        import pdb;pdb.set_trace()

    if len(msg) < max_tweet_len:
        return msg
    msg = tweets['short']
    if not isinstance(msg, unicode):
        msg = msg.decode('utf-8')
    msg = msg.format(title=title,
                     rank=article['rank'],
                     project=project)
    if len(msg) < max_tweet_len:
        return msg
    msg = tweets['short']
    if not isinstance(msg, unicode):
        msg = msg.decode('utf-8')
    msg = msg.format(title=title[:50] + '...',
                     rank=article['rank'],
                     project=project)
    return msg


@tlog.wrap('critical')
def make_article_list(query_date, lang, project):
    wiki_info = get_wiki_info(lang, project)
    raw_traffic = get_traffic(query_date, lang, project)
    articles = [a for a in raw_traffic if is_article(a['article'], wiki_info)]
    prev_traffic = load_prev_traffic(query_date, 10, lang, project)
    tweet_templates = get_tweet_templates(lang)
    ret = []
    for article in articles:
        title = article['article']
        if not prev_traffic:
            prev_article = {}
        else:
            prev_article = prev_traffic[0].get(title, {})
        permalink = PERMALINK_TMPL.format(lang=lang,
                                          project=project,
                                          year=query_date.year,
                                          month=query_date.month,
                                          day=query_date.day,
                                          title=title)
        streak = find_streaks(title, prev_traffic)
        article.update(streak)
        article['views_short'] = shorten_number(article['views'])
        article['url'] = 'https://%s.%s.org/wiki/%s' % (lang, project, title)
        article['title'] = title.replace('_', ' ')
        article['permalink'] = permalink.encode('utf-8')
        article['rank'] = len(ret) + 1
        article['pviews'] = prev_article.get('views', None)
        article['prank'] = prev_article.get('rank', None)
        if not article['pviews'] or article['views'] > article['pviews']:
            article['view_trend'] = '&uarr;'
        elif article['views'] == article['pviews']:
            article['view_trend'] = None
        else:
            article['view_trend'] = '&darr;'
        if not article['prank'] or article['rank'] < article['prank']:
            article['rank_trend'] = '&uarr;'
        elif article['rank'] == article['prank']:
            article['rank_trend'] = None
        else:
            article['rank_trend'] = '&darr;'
        if article['pviews']:
            view_delta = abs(article['views'] - article['pviews'])
            article['view_delta'] = shorten_number(view_delta)
        else:
            article['view_delta'] = shorten_number(article['views'])
        tweet = tweet_composer(article, lang, project, tweets=tweet_templates)
        article['tweet'] = quote_plus(tweet.encode('utf-8'), safe=':/')
        ret.append(article)
    return ret


@tlog.wrap('info', inject_as='log_rec')
def add_extras(articles, lang, project, log_rec):
    '''\
    Add images and summaries to articles in groups.
    '''
    log_rec['len_art'] = len(articles)
    ret = []
    article_groups = chunked(articles, DEFAULT_GROUP_SIZE)
    for article_group in article_groups:
        titles = [a['article'] for a in article_group]
        images = get_images(titles, lang, project)
        summaries = get_summaries(titles, lang, project)

        for article in article_group:
            title = article['title']
            article['image_url'] = images.get(title, DEFAULT_IMAGE)
            if word_filter(title) or word_filter(article['image_url']):
                article['image_url'] = DEFAULT_IMAGE
            summary = summaries.get(title, '')
            summary = crisco.shorten(summary, lang, 400)
            article['summary'] = summary
            ret.append(article)

    log_rec.success('finished adding images/summaries for {len_art} articles')
    return ret


def save_traffic_stats(lang, project, query_date, limit=DEFAULT_LIMIT):
    '''\
    1. Get articles
    2. Add images and summaries
    3. Prepare and save results
    '''
    articles = make_article_list(query_date,
                                 lang=lang,
                                 project=project)
    total_traffic = get_project_traffic(query_date, lang, project)
    articles = articles[:limit]
    articles = add_extras(articles, lang=lang, project=project)
    ret = {'articles': articles,
           'formatted_date': format_date(query_date,
                                         format='d MMMM yyyy',
                                         locale=lang),
           'date': {'day': query_date.day,
                    'month': query_date.month,
                    'year': query_date.year},
           'lang': lang,
           'full_lang': LOCAL_LANG_MAP[lang],
           'total_traffic': total_traffic,
           'total_traffic_short': shorten_number(total_traffic),
           'examples': [articles[0],
                        articles[1],
                        articles[2],
                        articles[query_date.day * 2]],  # haha ok..
           'project': project.capitalize(),
           'permalink': DATE_PERMALINK_TMPL.format(lang=lang,
                                                   project=project,
                                                   year=query_date.year,
                                                   month=query_date.month,
                                                   day=query_date.day),
           'meta': {'fetched': datetime.utcnow().isoformat()}}
    outfile_name = DATA_PATH_TMPL.format(lang=lang,
                                         project=project,
                                         year=query_date.year,
                                         month=query_date.month,
                                         day=query_date.day)

    with tlog.critical('saving_single_day_stats') as rec:
        rec['out_file'] = os.path.abspath(outfile_name)
        try:
            out_file = codecs.open(outfile_name, 'w')
        except IOError:
            mkdir_p(os.path.dirname(outfile_name))
            out_file = codecs.open(outfile_name, 'w')
        with out_file:
            data_bytes = json.dumps(ret, indent=2, sort_keys=True)
            rec['len_bytes'] = len(data_bytes)
            out_file.write(data_bytes)

        rec.success('wrote {len_bytes} bytes to {out_file}')

    return


@tlog.wrap('backfill', inject_as='log_rec')
def backfill(lang, project, days, update, log_rec):
    for day in range(int(days), 1, -1):
        input_date = date.today() - timedelta(days=day)
        save_traffic_stats(lang, project, input_date)
        if update:
            update_charts(input_date, lang, project)

    log_rec.success('finished backfilling {} days', days)
    return


def get_argparser():
    desc = 'Generate your Wikipedia traffic report'
    prs = ArgumentParser(description=desc)
    prs.add_argument('--lang', default=DEFAULT_LANG)
    prs.add_argument('--limit', default=DEFAULT_LIMIT)
    prs.add_argument('--project', default=DEFAULT_PROJECT)
    prs.add_argument('--date', default=None)
    prs.add_argument('--backfill', default=None)
    prs.add_argument('--update', '-u', action='store_true')
    prs.add_argument('--poll',
                     help="length of time to poll (e.g., 5m, 4h, 1h30m")
    prs.add_argument('--poll-interval',
                     help="length of time between poll attempts")
    return prs


def main():
    parser = get_argparser()
    args = parser.parse_args()
    if args.backfill:
        backfill(args.lang, args.project, args.backfill, args.update)
        return

    if not args.date:
        input_date = date.today()
    else:
        input_date = datetime.strptime(args.date, '%Y%m%d').date()

    if args.poll:
        poll_td = parse_timedelta(args.poll)
        if args.poll_interval:
            poll_interval = parse_timedelta(args.poll_interval)
        else:
            poll_interval = POLL_INTERVAL

        # if args.poll % POLL_INCR_MINS:
        #     raise ValueError('poll time must be in increments of %r minutes'
        #                      % POLL_INCR_MINS)
        err_write = sys.stderr.write
        count = 0
        max_time = datetime.now() + poll_td
        while 1:
            count += 1
            try:
                save_traffic_stats(args.lang, args.project, input_date)
                break
            except (urllib2.HTTPError, urllib2.URLError) as he:
                # tried to be nice but the API gives back all sorts of statuses
                # if he.getcode() != 404:
                #     raise
                try:
                    status_code = he.getcode()
                except:
                    status_code = he
                if (datetime.now() + poll_interval) <= max_time:
                    if count == 1:
                        err_write('# ' + datetime.now().isoformat())
                        err_write(' - got %s - polling every %r mins until %s.\n'
                                  % (status_code,
                                     poll_interval.total_seconds() / 60.0,
                                     max_time.isoformat()))
                    time.sleep(poll_interval.total_seconds())
                else:
                    err_write('\n!! - ')
                    err_write(datetime.now().isoformat())
                    err_write(' - no results after %r attempts and %r minutes,'
                              ' exiting.\n\n' % (count,
                                                 poll_td.total_seconds() / 60))
                    break
    else:
        save_traffic_stats(args.lang, args.project, input_date)
    if args.update:
        print update_charts(input_date, args.lang, args.project)
    #if DEBUG:
    #    import pdb
    #    pdb.set_trace()


if __name__ == '__main__':
    main()
