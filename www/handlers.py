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

# -----------------------------------------管理用户----------------------------------------------
@get('/show_all_users')
async def show_all_users():
    users = await User.findAll()
    logging.info('to index...')
    return {
        '__template__': 'all_users.html',
        'users:': users
    }


