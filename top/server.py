from os import path
from datetime import datetime, timedelta

from clastic import Application, redirect

from common import HTML_FILE_TMPL, DEFAULT_LANG, DEFAULT_PROJECT
from build_page import check_issue


def redirect_today(lang=DEFAULT_LANG, project=DEFAULT_PROJECT):
    cur_date = datetime.today()
    days = 0
    while not check_issue(cur_date, days, lang, project):
        days += 1
    cur_date = cur_date - timedelta(days=days)
    today_file = HTML_FILE_TMPL.format(lang=DEFAULT_LANG,
                                       project=DEFAULT_PROJECT,
                                       year=cur_date.year,
                                       month=cur_date.month,
                                       day=cur_date.day)
    return redirect(today_file)

if __name__ == '__main__':
    routes = [('/', redirect_today)]
    static_dir = path.abspath(path.join(path.dirname(__file__), 'static'))
    app = Application(routes)
    app.serve(static_path=static_dir, static_prefix='')
