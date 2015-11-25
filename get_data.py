# -*- coding: utf-8 -*-
import os
import codecs
import urllib2
from itertools import takewhile
from json import load, loads, dump
from argparse import ArgumentParser
from urllib import urlencode, quote_plus
from datetime import date, timedelta, datetime

from boltons.fileutils import mkdir_p

from utils import grouper, shorten_number
from word_filter import word_filter
from common import (DATA_PATH_TMPL,
                    TOP_API_URL,
                    MW_API_URL,
                    DEBUG,
                    PREFIXES,
                    LOCAL_LANG_MAP,
                    DEFAULT_PROJECT,
                    DEFAULT_LANG)

DEFAULT_LIMIT = 100
DEFAULT_IMAGE = 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/'\
                'Wikipedia%27s_W.svg/400px-Wikipedia%27s_W.svg.png'
DEFAULT_SUMMARY = None
DEFAULT_GROUP_SIZE = 20


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
    data = loads(resp.read())
    mainpage = data['query']['general']['mainpage'].replace(' ', '_')
    namespaces = [ns_info['*'].replace(' ', '_') for ns_id, ns_info in
                  data['query']['namespaces'].iteritems() if ns_id is not 0]
    return {'mainpage': mainpage, 'namespaces': namespaces}


def is_article(title, wiki_info):
    '''\
    Is it an article, or some other sort of page? We'll want to filter out the
    search page (Special:Search in English, etc) and similar pages appearing
    inconveniently in the traffic report.
    '''
    skip = ['-'] + [wiki_info['mainpage']]
    prefixes = PREFIXES + wiki_info['namespaces']
    if title in skip:
        return False
    for prefix in prefixes:
        if title.startswith(prefix + ':'):
            return False
    return True


def get_query(params, lang, project, extractor, default_val):
    '''\
    Generic function for MediaWiki queries.
    '''
    url = MW_API_URL.format(lang=lang, project=project)
    resp = urllib2.urlopen(url + urlencode(params))
    data = loads(resp.read())
    ret = {}
    for page_id, page_info in data['query']['pages'].iteritems():
        if int(page_id) < 0:
            ret[page_info['title']] = default_val
        else:
            try:
                ret[page_info['title']] = extractor(page_info)
            except Exception as e:
                ret[page_info['title']] = default_val
    return ret


def get_images(titles, lang, project):
    '''\
    Get thumbnails for a group of pages via MediaWiki API.
    '''
    params = {'action': 'query',
              'prop': 'pageimages',
              'pithumbsize': 500,
              'pilimit': 50,
              'format': 'json',
              'titles': '|'.join(titles).encode('utf-8')}
    extractor = lambda page: page.get('thumbnail', {}).get('source',
                                                           DEFAULT_IMAGE)
    images = get_query(params, lang, project, extractor, DEFAULT_IMAGE)
    return images


def get_summaries(titles, lang, project):
    '''\
    Get summaries for a group of pages via MediaWiki API.
    '''
    params = {'action': 'query',
              'prop': 'extracts',
              'exsentences': 2,
              'explaintext': 1,
              'exintro': 1,
              'exlimit': 20,
              'format': 'json',
              'titles': '|'.join(titles).encode('utf-8')}
    extractor = lambda page: page['extract']
    summaries = get_query(params, lang, project, extractor, DEFAULT_SUMMARY)
    return summaries


def get_article_traffic(query_date, lang, project):
    '''\
    Get the traffic report for the top 1000 articles for a given day.
    '''
    url = TOP_API_URL.format(lang=lang,
                             project=project,
                             year=query_date.year,
                             month=query_date.month,
                             day='%02d' % query_date.day)
    if DEBUG:
        print 'Getting %s' % url
    resp = urllib2.urlopen(url)
    data = loads(resp.read())
    articles = data['items'][0]['articles']
    return articles


def load_prev_stats(query_date, limit=10, lang=DEFAULT_LANG,
                    project=DEFAULT_PROJECT):
    '''\
    Load available local traffic data.
    '''
    prev_stats = []
    for lookback in range(1, limit):
        prev = query_date - timedelta(days=lookback)
        prevfile_name = DATA_PATH_TMPL.format(lang=lang,
                                              project=project,
                                              year=prev.year,
                                              month=prev.month,
                                              day=prev.day)
        try:
            data_file = codecs.open(prevfile_name, 'r')
        except IOError:
            print 'No file for %s' % prev.strftime('%Y%m%d')
            break
        with data_file:
            prev_stats.append(dict((art['article'], art) for art in
                                   load(data_file)['articles']))
    return prev_stats


def find_streaks(article_titles, prev_stats):
    '''\
    Look for streaks in previous data.
    '''
    ret = {}
    for article in article_titles:
        ret[article] = [l[article]['rank'] if l.get(article) else None
                        for l in prev_stats]
        streak = [a for a in takewhile(lambda r: r, ret[article])]
        if len(streak) > 0:
            try:
                streak_min = min(ret[article])
            except Exception as e:
                # import pdb; pdb.set_trace()
                raise e
        else:
            streak_min = None
        ret[article] = (len(streak), streak_min)
    return ret


def tweet_composer(article, lang, project):
    '''\
    Compose a short tweet for an article based on its stats and a few
    templates.
    '''
    max_tweet_len = 118  # Plus room for link
    title = article['title']
    project = project.capitalize()
    lang = LOCAL_LANG_MAP[lang]
    if type(article['streak']) is str:
        streak = article['streak'].replace('+', '')
    else:
        streak = article['streak']
    if int(streak) > 1:
        msg = 'On a %s day streak, %s was the #%s most read article on %s #%s'\
            ' w/ %s views' % (article['streak'],
                              title,
                              article['rank'],
                              lang,
                              project,
                              article['views'])
        if len(msg) < max_tweet_len:
            return msg
    msg = '%s was viewed %s times on %s #%s' % (title,
                                                article['views'],
                                                lang,
                                                project)
    if len(msg) < max_tweet_len:
        return msg
    msg = '%s was #%s on #%s' % (title, article['rank'], project)
    if len(msg) < max_tweet_len:
        return msg
    msg = '%s was #%s on #%s' % (title[:50] + '...', article['rank'], project)
    return msg


def make_article_list(query_date, limit, lang, project):
    # TODO: Clean up
    wiki_info = get_wiki_info(lang, project)
    cur_articles = get_article_traffic(query_date, lang, project)
    cur_articles = [art for art in cur_articles
                    if is_article(art['article'], wiki_info)]
    prev = query_date - timedelta(days=1)
    prev_articles = get_article_traffic(prev, lang, project)
    prev_articles = dict((art['article'], art) for art in prev_articles
                         if is_article(art['article'], wiki_info))
    prev_stats = load_prev_stats(query_date)
    max_streak = len(prev_stats) + 1
    streaks = find_streaks([a['article'] for a in cur_articles], prev_stats)
    ret = []
    for article in cur_articles:
        prev_article = prev_articles.get(article['article'], {})
        article['pviews'] = prev_article.get('views', None)
        article['prank'] = prev_article.get('rank', None)
        if article['pviews'] and article['pviews'] < article['views']:
            article['view_trend'] = '&uarr;'
        elif not article['pviews']:
            article['view_trend'] = '&uarr;'
        elif article['views'] == article['pviews']:
            article['view_trend'] = '-'
        else:
            article['view_trend'] = '&darr;'
        if article['prank'] and article['rank'] < article['prank']:
            article['rank_trend'] = '&uarr;'
        elif not article['prank']:
            article['rank_trend'] = '&uarr;'
        elif article['rank'] == article['prank']:
            article['rank_trend'] = '-'
        else:
            article['rank_trend'] = '&darr;'
        if article['pviews']:
            article['view_delta'] = shorten_number(abs(article['views'] -
                                                   article['pviews']))
        else:
            article['view_delta'] = None
        (streak, rank_max) = streaks.get(article['article'], (0, None))
        streak = streak + 1
        if streak == max_streak:
            streak = '%s+' % (streak - 1,)
        article['max_streak'] = max_streak
        article['streak'] = streak
        article['rank'] = len(ret) + 1
        article['views_raw'] = article['views']
        article['views'] = shorten_number(article['views'])
        article['url'] = 'https://%s.%s.org/wiki/%s' % (lang,
                                                        project,
                                                        article['article'])
        article['title'] = article['article'].replace('_', ' ')
        article['tweet'] = quote_plus(tweet_composer(article,
                                                     lang,
                                                     project).encode('utf-8'),
                                      safe=':/')
        ret.append(article)
    return ret[:limit]


def add_extras(articles, lang, project):
    '''\
    Add images and summaries to articles in groups.
    '''
    ret = []
    article_groups = grouper(articles, DEFAULT_GROUP_SIZE)
    for article_group in article_groups:
        titles = [a['article'] for a in article_group]
        if DEBUG:
            print 'Getting images for %s articles' % len(titles)
        images = get_images(titles, lang, project)
        if DEBUG:
            print 'Getting summaries for %s articles' % len(titles)
        summaries = get_summaries(titles, lang, project)
        if DEBUG:
            print 'Preparing results...'
        for article in article_group:
            title = article['title']
            article['image_url'] = images[title]
            if word_filter(title) or word_filter(article['image_url']):
                print 'no image for %s' % (title,)
                article['image_url'] = DEFAULT_IMAGE
            article['summary'] = summaries[title]
            ret.append(article)
    return ret


def save_traffic_stats(lang, project, query_date, limit=DEFAULT_LIMIT):
    '''\
    1. Get articles
    2. Add images and summaries
    3. Prepare and save results
    '''
    articles = make_article_list(query_date,
                                 limit=limit,
                                 lang=lang,
                                 project=project)
    articles = add_extras(articles, lang=lang, project=project)
    ret = {'articles': articles,
           'formatted_date': query_date.strftime('%d %B %Y'),
           'date': {'day': query_date.day,
                    'month': query_date.month,
                    'year': query_date.year},
           'lang': lang,
           'full_lang': LOCAL_LANG_MAP[lang],
           'examples': [articles[0], articles[query_date.day*2]],
           'project': project.capitalize(),
           'meta': {'generated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}}
    outfile_name = DATA_PATH_TMPL.format(lang=lang,
                                         project=project,
                                         year=query_date.year,
                                         month=query_date.month,
                                         day=query_date.day)
    try:
        out_file = codecs.open(outfile_name, 'w')
    except IOError:
        mkdir_p(os.path.dirname(outfile_name))
        out_file = codecs.open(outfile_name, 'w')
    with out_file:
        if DEBUG:
            print 'Saving %s ...' % outfile_name
        dump(ret, out_file)


def get_argparser():
    desc = 'Generate your Wikipedia traffic report'
    prs = ArgumentParser(description=desc)
    prs.add_argument('--lang', default=DEFAULT_LANG)
    prs.add_argument('--limit', default=DEFAULT_LIMIT)
    prs.add_argument('--project', default=DEFAULT_PROJECT)
    prs.add_argument('--date', default=None)
    prs.add_argument('--update', '-u', action='store_true')
    return prs


if __name__ == '__main__':
    parser = get_argparser()
    args = parser.parse_args()
    if not args.date:
        input_date = date.today() - timedelta(days=1)
    else:
        input_date = datetime.strptime(args.date, '%Y%m%d')
    save_traffic_stats(args.lang, args.project, input_date)
    if args.update:
        from build_page import save_and_update
        print save_and_update(input_date, args.lang, args.project)
    if DEBUG:
        import pdb
        pdb.set_trace()
