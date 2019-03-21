#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/7/17
# @Author: lsj
# @File  : unpkg.py
# @Desc  : 
默认Python版本支持：3.6
"""
import os
import re
import shutil
import time

import requests

_url = "https://unpkg.com/"
mod = "ionicons"  # <===需要下载的模块名称
version = ""
headers = {
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Content-Type': 'text/html;Charset=utf-8',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101 Firefox/61.0"
}


# 获取HTML
def get_html(url, encoding='utf-8'):
    rd = requests.get(url, params=None, headers=headers)
    rd.encoding = encoding
    return rd.text


# 获取版本
def get_versions(m):
    h = get_html(url + m + '/')
    j = re.findall(r'<select id="version">(.*?)</select>', h, re.S)[0]
    patt = re.compile(r'<option.+?>(.+?)</option>')
    option = patt.findall(j)
    return option


# 扫描目录
def get_paths(v, p='/', files=None, folders=None):
    if files is None:
        files = []
    if folders is None:
        folders = []
    h = get_html(url + v + p)
    t = re.findall(r'<table>(.*?)</table>', h, re.S)[0]
    href = re.findall('href="(.*?)"', t)
    for name in href:
        path = p + name
        if name in ['../', 'LICENSE'] or path in ['/src/']:  # 根据实际需要 跳过
            continue
        print(path)
        if name[-1] == '/':
            folders.append(path)
            get_paths(v, path, files, folders)
        else:
            files.append(path)
    return {"files": files, "folders": folders}


# 创建目录
def make_dirs(dirs, p):
    if p is None:
        p = './'
    for i in dirs:
        path = p + i
        if not os.path.exists(path):
            print("创建目录", path)
            os.makedirs(path)


# 下载文件
def download(url, path=None):  # dir=保存文件夹路径
    if not os.path.exists(path):
        print("下载:", url)
        r = requests.get(url)
        t = str(time.time()) + '.tmp'
        open(t, 'wb').write(r.content)
        shutil.move(t, path)
    else:
        print("文件已存在")


def main():
    global version
    print(_url + mod + '/')
    versions = get_versions(mod)
    print("所有版本:", versions)
    version = version if version else versions[-1]  # <====定义下载的模块版本
    print("默认版本:", version)
    paths = get_paths(version)
    make_dirs(paths["folders"], version)
    for i in paths["files"]:
        u = _url + version + i
        download(u, version + '/' + i)
    print("完成")


if __name__ == '__main__':
    main()
