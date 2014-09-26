#!/usr/bin/env python
#coding:utf8

import os
import string
from urllib import unquote
from json import dumps as jsondumps

import tornado.ioloop
import tornado.web

from utils.readelf import do_deep_lookupsymbol,do_quick_lookupsymbol,\
        do_get_basic_elf_info
from utils.utils import *

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        items = ['Ubuntu', 'Centos', ]
        self.render('index.html',title = 'this is test title', items=items)

def getNodeDic(text, attributes=[]):
    global i
    i = 0
    node = {}
    node["id"]   = i
    node['text'] = text
    node['state'] = "close"
    node['children'] = []
    # node['attributes'] = attributes
    i = i + 1
    return node

# FIXME this code need to be rewrite for more readable
# addition, triple for loop is too ugly
def getTreeJson():
    treeJson = []
    for distribution in vmlinux_file_json.keys():
        NodeDisDic = getNodeDic(distribution)
        for release_code in vmlinux_file_json[distribution].keys():
            NodeRelDic = getNodeDic(release_code)
            for vmlinux_file in   \
                vmlinux_file_json[distribution][release_code]:
                NodeRelDic['children'].append(getNodeDic(vmlinux_file))
            NodeDisDic['children'].append(NodeRelDic)
        treeJson.append(NodeDisDic)
    return treeJson

class ListDirHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(" *] [* Not Support for GET Request ")
    def post(self):
        jsondata = self.request.body
        # a bug : easyui reject ' but "
        self.write(str(getTreeJson()).replace('\'','"'))

class SearchSymbolHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(" *] [* Not Support for GET Request ")
    def post(self):
        # 特别要注意，因为是响应的ajax的请求，返回数据类型需指定为json
        uri = self.request.body
        vmlinux_dir = self.get_argument("onSelectKverion", None)
        ksymbol = self.get_argument("Ksym", None)
        quick_lookup = self.get_argument("QuickLookup", True)

        if not vmlinux_dir or not ksymbol:
            self.write("{'error': 'please supply vmlinux_dir&ksymbol'")
            return
        # remove unsafe string
        safe_string = string.ascii_letters + string.digits +"&=/"
        uri = unquote(uri)
        for i in range(len(uri)):
            if uri[i] not in safe_string:
                uri = uri.replace(uri[i], '_')
        if '&' not in uri:
            self.write("{'error' : 'we need to select kernel&&supply ksym'}")
            return
        # FIXME 拼接成绝对路径 这样做似乎并不十分安全
        vmlinux_dir = webui_setting['vmlinux_abs_dir'] + vmlinux_dir
        try:
            fd = open(vmlinux_dir)
        except:
            self.write("SearchSymbolHandler::can't open vmlinux,check vmlinux_abs_dir")

        if quick_lookup is True:
            result = do_quick_lookupsymbol(ksymbol, fd)
        else:
            result = do_deep_lookupsymbol(ksymbol, fd)
        fd.close()
        result = result.replace("\n", "<br>")
        self.write('{"%s":"%s"}' % (ksymbol, result))

class GetBasicInfoHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("NotImplemented")
    def post(self):
        vmlinux_dir = self.get_argument("onSelectKverion", None)
        vmlinux_dir = webui_setting['vmlinux_abs_dir'] + vmlinux_dir
        try:
            fd = open(vmlinux_dir)
        except:
            self.write("SearchSymbolHandler::can't open vmlinux,check vmlinux_abs_dir")
            return
        result = do_get_basic_elf_info(fd)
        fd.close()
        result = result.replace("\n", "<br>")
        self.write(result)


settings = {
        "cookie_secret": "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
        # "xsrf_cookies": True,
        'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
        'static_path':  os.path.join(os.path.dirname(__file__), 'static')
        }

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/index*", MainHandler),
    (r"/search/*", SearchSymbolHandler),
    (r'/listdir/', ListDirHandler),
    (r'/getBasicInfo/', GetBasicInfoHandler),
    ], **settings)

webui_setting = {
        'vmlinux_abs_dir' : '/mnt/Ksymhunter/',
        }
vmlinux_file_json = getVmlinuxJson(webui_setting['vmlinux_abs_dir'])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

