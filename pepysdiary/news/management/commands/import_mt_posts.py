# coding: utf-8
import MySQLdb
from optparse import make_option
import pytz

from django.conf import settings
from django.core.management.base import BaseCommand

from pepysdiary.common.utilities import fix_old_links
from pepysdiary.news.models import Post


class Command(BaseCommand):
    """
    Gets all the Site News Posts from the MovableType MySQL database and
    creates a new Django object for each one.

    Usage:
    $ ./manage.py import_mt_articles
    """
    option_list = BaseCommand.option_list + (
        make_option('--all',
            action='store_true',
            dest='all',
            default=True,
            help="Import all Site News Posts from legacy MT MySQL database. (Default)"),
    )
    args = ''
    help = "Imports Site News Posts from legacy MT MySQL database."

    def handle(self, *args, **options):

        # Mapping MT Category IDs to new values.
        categories = {
            '225': Post.CATEGORY_EVENTS,
            '222': Post.CATEGORY_HOUSEKEEPING,
            '223': Post.CATEGORY_FEATURES,
            '224': Post.CATEGORY_MEDIA,
            '220': Post.CATEGORY_PRESS,
            '221': Post.CATEGORY_STATISTICS,
        }

        db = MySQLdb.connect(host=settings.MT_MYSQL_DB_HOST,
                            user=settings.MT_MYSQL_DB_USER,
                            passwd=settings.MT_MYSQL_DB_PASSWORD,
                            db=settings.MT_MYSQL_DB_NAME,
                            charset='utf8',
                            use_unicode=True)
        cur = db.cursor(MySQLdb.cursors.DictCursor)

        # FETCH THE DIARY ENTRIES.

        cur.execute("SELECT entry_id, entry_title, entry_text, "
            "entry_text_more, "
            "entry_created_on, entry_authored_on "
            "FROM mt_entry WHERE entry_blog_id='%s'" % (
                                                settings.MT_NEWS_BLOG_ID))

        rows = cur.fetchall()
        for row in rows:
            print '%s %s' % (row['entry_id'], row['entry_title'])

            # Fix any old-style links in the two text fields.
            if row['entry_text'] is None:
                intro = u''
            else:
                intro = fix_old_links(row['entry_text'])
            if row['entry_text_more'] is None:
                text = u''
            else:
                text = fix_old_links(row['entry_text_more'])

            # Get the Post's MT Category.
            # Each entry is probably only in one category, but we only use one
            # per Post now so we only fetch the Primary one.
            cur.execute("SELECT placement_category_id FROM mt_placement "
                        "WHERE placement_entry_id='%s' AND "
                        "placement_is_primary='1'" % (row['entry_id']))
            cat_row = cur.fetchall()[0]
            category = categories[str(int(cat_row['placement_category_id']))]

            post = Post(id=row['entry_id'],
                        title=row['entry_title'],
                        intro=intro,
                        text=text,
                        date_published=row['entry_authored_on'].replace(
                                                            tzinfo=pytz.utc),
                        status=Post.STATUS_PUBLISHED,
                        category=category,
                    )
            post.save()

            # SET ORIGINAL CREATED TIME.
            created_time = row['entry_created_on'].replace(tzinfo=pytz.utc)
            post.date_created = created_time
            post.save()

        cur.close()
        db.close()