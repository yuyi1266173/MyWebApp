# -*- coding:utf-8 -*-
import re
import time
import json
import logging
import hashlib
import markdown2
from apis import APIValueError, APIResourceNotFoundError, APIError, APIPermissionError, Page
from aiohttp import web
from coroweb import get, post
from models import User, Blog, Comment, next_id
from ..conf.config import configs

"""
url handlers
"""

COOKIE_NAME = 'myblogsession'
_COOKIE_KEY = configs.session.secret

_RE_EMAIL = re.compile(r'^[0-9a-z\.\_\-]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


def user2cookie(user, max_age):
    """
    Generate cookie str by user(id-expires-sha1).
    """
    # build cookie string by: id-expires-sha1
    # 过期时间是创建时间+存活时间
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    # SHA1是一种单向算法，可以通过原始字符串计算出SHA1结果，但无法通过SHA1结果反推出原始字符串。
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


def text2html(text):
    # HTML转义字符
    # "     &quot;
    # &     &amp;
    # <     &lt;
    # >     &gt;
    # 不断开空格 &nbsp;

    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '%amp;').replace('<', '&alt;').replace('>', '&gt;'),
                filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

async def cookie2user(cookie_str):
    """
    Parse cookie and load user if cookie is valid.
    """
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '********'
        return user
    except Exception as e:
        logging.exception(e)
        return None

# -----------------------------------------管理用户----------------------------------------------
@get('/show_all_users')
async def show_all_users():
    users = await User.findAll()
    logging.info('to index...')
    return {
        '__template__': 'all_users.html',
        'users:': users
    }


