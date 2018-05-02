import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web


# 这个函数的作用就是当有http请求的时候，通过logging.info输出请求的信息，其中包括请求的方法和路径
async def logger_factory(app, handler):
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        # handler为处理函数，request为参数
        return await handler(request)
    return logger

# 请求对象request的处理工序流水线先后依次是：
#     	logger_factory->response_factory->RequestHandler().__call__->get或post->handler
# 对应的响应对象response的处理工序流水线先后依次是:
# 由handler构造出要返回的具体对象
# 然后在这个返回的对象上加上'__method__'和'__route__'属性，以标识别这个对象并使接下来的程序容易处理
# RequestHandler目的就是从请求对象request的请求content中获取必要的参数，调用URL处理函数,然后把结果返回给response_factory
# response_factory在拿到经过处理后的对象，经过一系列类型判断，构造出正确web.Response对象，以正确的方式返回给客户端
# 在这个过程中，只关心handler的处理，其他的都走统一通道，如果需要差异化处理，就在通道中选择适合的地方添加处理代码。
# 注：在response_factory中应用了jinja2来渲染模板文件
async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)
        logging.info('response result = %s' % str(r))
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        # 大多数返回的是dict
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False,
                                                    default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                # 对模板进行渲染
                r['__user__'] = request.__user__
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and 600 > r >= 100:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            status_code, description = r
            if isinstance(status_code, int) and 600 > status_code >= 100:
                return web.Response(status=status_code, text=str(description))
        # default:
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


def index(request):
    return web.Response(body=b'<h1>Awesome</h1>')

@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
