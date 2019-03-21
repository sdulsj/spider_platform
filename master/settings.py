#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

# 本地主机参数
# socket.gethostbyname(socket.getfqdn(socket.gethostname()))
LOCALHOST_HOST = "127.0.0.1"  # 本机IP  127.0.0.1
LOCALHOST_PORT = 8080  # 本机端口  8080  5000
DEPLOY_HOST = 'localhost'
DEPLOY_PORT = 6800

# 目录/路径参数
DIR_CURR = os.path.dirname(os.path.realpath(__file__))  # 当前目录
DIR_ROOT = DIR_CURR  # 根目录
DIR_EXEC = os.path.join(DIR_ROOT, "scripts")  # 执行目录
DIR_EGGS = os.path.join(DIR_EXEC, "eggs")  # 蛇蛋目录
DIR_LOGS = os.path.join(DIR_EXEC, "logs")  # 日志目录

LOG_LEVEL = "INFO"  # DEBUG/INFO/WARNING/ERROR/CRITICAL

# MySQL配置 from urllib.parse import quote_plus
# 数据库+数据库驱动://数据库用户名:密码@主机地址:端口/数据库?编码
# mysql+pymysql://{}:{}@{}:{}/{}?charset={}
MYSQL_KWARGS = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "alalei999",
    "database": "test_sp3",
    "charset": "utf8",
}

# InfluxDB配置
INFLUX_KWARGS = {
    "host": "127.0.0.1",
    "port": 8086,
    "username": "root",
    "password": "alaleiroot",
    "database": "spider_platform",
}

# Email配置
MAIL_KWARGS = {
    "host": "smtp.exmail.qq.com",
    "port": 465,
    "username": "mixtmt@cdv.com",  # mixtmt@cdv.com
    "password": "",
    "use_ssl": True,
    "sender": "mixtmt@cdv.com",  # mixtmt@cdv.com
    "recipients": ["mixtmt@cdv.com"],
}
