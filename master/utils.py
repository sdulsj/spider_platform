#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import functools
import hashlib
import inspect
import logging
import mimetypes
import netrc
import os
import queue
import re
import smtplib
import socket
import time
import traceback
from base64 import urlsafe_b64encode
from email.encoders import encode_base64
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import parseaddr, formataddr, formatdate
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

import aiohttp
import pymysql
from influxdb import InfluxDBClient


# 计算MD5值
def get_md5(*args, sep: str = "#"):
    if not args:
        return
    md5 = hashlib.md5()
    md5.update(sep.join([str(s) for s in args]).encode("utf-8"))
    return md5.hexdigest()
    pass


# 计算MD5值
def get_md5_value(src):
    md5 = hashlib.md5()
    md5.update(src)
    return md5.hexdigest()


def get_logger(name=None, log_file=None, log_level=logging.INFO):
    # https://github.com/aresowj/self-library/blob/master/Python/logger.py

    logger = logging.getLogger(name)

    # %(name)s - %(levelname)s - %(message)s
    formatter = logging.Formatter(
        "%(name)s - %(asctime)s - %(module)s.%(funcName)s.%(lineno)d - "
        "%(levelname)s - %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    rotate_handler = RotatingFileHandler(log_file, 'a', 1024 * 1024 * 10, 5)
    rotate_handler.setFormatter(formatter)
    logger.addHandler(rotate_handler)

    logger.setLevel(log_level)  # 'INFO'

    return logger
    pass


def seconds2time(seconds):
    if not seconds:
        return
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)
    pass


def datetime2str(date_time):
    if not date_time:
        return
    if not isinstance(date_time, datetime.datetime):
        return
    return date_time.strftime('%Y-%m-%d %H:%M:%S')
    pass


def time_difference(t1, t2):
    if not t1 or not t2:
        return
    return int(time.mktime(t2.timetuple()) - time.mktime(t1.timetuple()))
    pass


class MySQLHelper(object):
    def __init__(self, host=None, port=3306, user=None, password="",
                 database=None, charset='utf8'):
        """
        初始化类实例
        :param host: 域名
        :param port: 端口
        :param user: 用户
        :param password: 密码
        :param database: 数据库
        :param charset: 编码
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset

        self.conn = pymysql.connect(host=host, port=port, user=user,
                                    password=password, database=database,
                                    charset=charset)
        self.cursor = self.conn.cursor()
        pass

    def open(self):
        try:
            self.conn = pymysql.connect(host=self.host, port=self.port,
                                        user=self.user, password=self.password,
                                        database=self.database,
                                        charset=self.charset)
            self.cursor = self.conn.cursor()
            pass
        except Exception as e:
            logging.error('{}==>{}'.format(type(e), e), exc_info=True)
        pass

    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        pass

    # 执行SQL
    def exec_sql(self, sql, *args):
        """
        执行SQL
        :param sql: SQL语句
        :param args: SQL语句数据列
        :return:
        """
        try:
            if not args:
                self.cursor.execute(sql)
                if re.match(pattern=r'^(SELECT|EXEC|CALL)[\s\S]+$', string=sql,
                            flags=re.I):
                    return self.cursor.fetchall()
            elif isinstance(args[0], (str, bytes)):
                self.cursor.execute(sql, args)
            else:
                self.cursor.executemany(sql, args)
        except Exception as ex:
            self.conn.rollback()
            raise ex
            # logging.error('{}==>{}'.format(type(ex), ex))
        finally:
            self.conn.commit()
        pass

    pass


class InfluxDBHelper(object):
    def __init__(self, host='localhost', port=8086, username='root',
                 password='root', database=None):
        """
        初始化类实例
        :param host: 域名
        :param port: 端口
        :param username: 用户
        :param password: 密码
        :param database: 数据库
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database

        self.conn = None
        self.open()
        pass

    def open(self):
        """打开数据库连接"""
        try:
            self.conn = InfluxDBClient(host=self.host, port=self.port,
                                       username=self.username,
                                       password=self.password,
                                       database=self.database)
            if self.database not in self.conn.get_list_database():
                self.conn.create_database(self.database)
        except Exception as e:
            raise e
        pass

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
        pass

    def __format_index(self, key, value):
        """
        格式化指标数据
        :param key: 指标类（表名）
        :param value: 指标值
        :return:
        """
        # tags 和 timestamp相同时数据会执行覆盖操作，相当于InfluxDB的更新操作
        json_data = {
            "measurement": key,
            "tags": {
                "host": self.localhost,
            },
            # "time": None,  # 时间不用设置,使用数据库默认生成的时间戳
            "fields": {
                "value": float(value)
            }
        }
        return json_data
        pass

    # 发送指标
    def send_value(self, key, value):
        """
        发送指标
        :param key: 指标类（表名）
        :param value: 指标值
        :return:
        """
        json_body = [self.__format_index(key, value)]
        self.conn.write_points(json_body)
        pass

    def batch_send_value(self, **kwargs):
        """
        批量发送指标
        :param kwargs: 指标字典，例{'time&&db': '10', 'num': '30'}
        :return:
        """
        json_body = [self.__format_index(key, value) for key, value in
                     kwargs.items()]
        if json_body:
            self.conn.write_points(points=json_body, batch_size=len(json_body))
        pass

    def get_stats(self, *args, **kwargs):
        """
        获取某某前至今的统计状态
        CREATE DATABASE "spider_platform";
        show databases;   //查询当前的所有数据库
        use spider_platform;  //使用某个数据库
        show measurements;
        DROP CONTINUOUS QUERY cq_disk_usage_015s ON "spider_platform";
        DROP MEASUREMENT "disk_usage_015s";
        CREATE CONTINUOUS QUERY cq_disk_usage_015s ON "spider_platform" BEGIN \
        SELECT mean(value) as value INTO disk_usage_015s FROM disk_usage GROUP \
        BY time(15s),host END;

        CREATE CONTINUOUS QUERY <cq_name> ON <database_name>
        [RESAMPLE [EVERY <interval>] [FOR <interval>]] BEGIN
        SELECT <function>(<stuff>)[,<function>(<stuff>)] INTO
        <different_measurement> FROM <current_measurement> [WHERE <stuff>]
        GROUP BY time(<interval>)[,<stuff>] END
        :param args: table names
        :param kwargs: weeks/days/hours/minutes/seconds
        :return:
        """
        _queries = [
            '',
            '_015s',
            '_030s',
            '_060s',
            '_120s',
            '_360s',
            '_900s'
        ]  # 1h/6h/12h/1d/3d/7d/14d
        _timedelta = [
            0,
            60 * 60,
            6 * 60 * 60,
            12 * 60 * 60,
            1 * 24 * 60 * 60,
            3 * 24 * 60 * 60,
            7 * 24 * 60 * 60
        ]
        _tables = ['cpu', 'virtual_memory', 'swap_memory', 'disk_usage',
                   'disk_io_read', 'disk_io_write', 'net_io_sent',
                   'net_io_receive']
        if not args:
            args = _tables

        timedelta = kwargs.get('weeks', 0) * 7 * 24 * 60 * 60
        timedelta += kwargs.get('days', 0) * 24 * 60 * 60
        timedelta += kwargs.get('hours', 0) * 60 * 60
        timedelta += kwargs.get('minutes', 0) * 60
        timedelta += kwargs.get('seconds', 0)
        _query = _queries[-1]
        for i in range(0, len(_timedelta) - 1):
            if _timedelta[i] / 2 <= timedelta < _timedelta[i + 1]:
                _query = _queries[i]
                break
            pass
        multiplier = 1000000000
        _time = int(time.time() - timedelta) * multiplier
        sql = ""
        for _table in args:
            sql += 'SELECT time,host,value FROM '
            sql += "{} WHERE time>={};".format(_table + _query, _time)
        # print(sql)
        data = self.conn.query(sql)
        if not data:
            return {}
        result = {}
        for rs in (data if isinstance(data, list) else [data]):
            for series in rs.raw.get('series', []):
                key = series.get('name').replace(_query, '')
                temp = dict()
                for _time, _host, _value in series.get('values', []):
                    # %Y-%m-%d %H:%M:%S.%f
                    _time = _time.split('.')[0].replace('T', ' ')
                    if _host not in temp:
                        temp[_host] = []
                    else:
                        temp[_host].append([_time, _value])
                result[key] = temp
                pass
            pass
        return result
        pass

    pass


class MailerException(Exception):
    """ 邮件发送异常类 """
    pass


class NetworkError(MailerException):
    """ 网络异常类 """
    pass


# 邮件操作帮助类
class EmailOperationHelper(object):
    """
    邮件操作帮助类
    # '*************************
    # '* 邮件服务返回代码含义
    # '* 500 格式错误，命令不可识别（此错误也包括命令行过长）
    # '* 501 参数格式错误
    # '* 502 命令不可实现
    # '* 503 错误的命令序列
    # '* 504 命令参数不可实现
    # '* 211 系统状态或系统帮助响应
    # '* 214 帮助信息
    # '* 220  服务就绪
    # '* 221  服务关闭传输信道
    # '* 421  服务未就绪，关闭传输信道（当必须关闭时，此应答可以作为对任何命令的响应）
    # '* 250 要求的邮件操作完成
    # '* 251 用户非本地，将转发向
    # '* 450 要求的邮件操作未完成，邮箱不可用（例如，邮箱忙）
    # '* 550 要求的邮件操作未完成，邮箱不可用（例如，邮箱未找到，或不可访问）
    # '* 451 放弃要求的操作；处理过程中出错
    # '* 551 用户非本地，请尝试
    # '* 452 系统存储不足，要求的操作未执行
    # '* 552 过量的存储分配，要求的操作未执行
    # '* 553 邮箱名不可用，要求的操作未执行（例如邮箱格式错误）
    # '* 354 开始邮件输入，以.结束
    # '* 554 操作失败
    # '* 535 用户验证失败
    # '* 235 用户验证成功
    # '* 334 等待用户输入验证信息
    """

    def __init__(self, host, port=465, username=None, password=None,
                 use_ssl=True, sender=None, recipients=None, timeout=10):
        """
        邮件操作帮助类
        :param host: string smtp服务器地址
        :param port: int smtp服务器端口号 465/25
        :param username: string 用户名
        :param password: string 密码
        :param use_ssl: bool 是否启用ssl,默认True
        :param sender: string 发件人邮箱
        :param recipients: string/list 收件人邮箱（列表）
        :param timeout: int 超时时间,默认10s
        """
        # 邮件设置
        self.host = host  # 服务器 smtp.exmail.qq.com
        self.port = port  # 端口 465
        self.username = username  # 用户 ***@163.com
        self.password = password  # 口令 ******
        self.use_ssl = use_ssl  # 是否使用SSL安全协议
        self.sender = sender  # 自 ***@163.com
        self.recipients = recipients  # 至 [***@163.com, ]
        self.timeout = timeout  # 超时时间

        self.logger = logging.getLogger('Mailer')
        pass

    def send_mail(self, subject, content, *file_paths, **kwargs):
        """
        发送邮件主函数
        :param subject: 邮件主题
        :param content: 邮件正文
        :param file_paths: 邮件附件（列表）
        :param kwargs: dict 邮件服务器设置
            :keyword host: string smtp服务器地址
            :keyword port: int smtp服务器端口号
            :keyword username: string 用户名
            :keyword password: string 密码
            :keyword use_ssl: bool 是否启用ssl,默认True
            :keyword timeout: int 超时时间,默认10s
            :keyword sender: string 发件人邮箱
            :keyword recipients: string/list 收件人邮箱（列表）
        :raise: NetworkError/MailerException
        :return:
        """
        # 重新赋值邮件配置
        host = kwargs.get("host") or self.host
        port = kwargs.get("port") or self.port
        username = kwargs.get("username") or self.username
        password = kwargs.get("password") or self.password
        use_ssl = kwargs.get("use_ssl") or self.use_ssl
        timeout = kwargs.get("timeout") or self.timeout
        sender = kwargs.get("sender") or self.sender
        recipients = kwargs.get("recipients") or self.recipients

        # 邮件类型
        content_type = 'html' if content.startswith('<html>') else 'plain'

        # 构造MIMEMultipart对象做为根容器  # 格式化邮件数据
        msg = MIMEMultipart()
        msg.set_charset("utf-8")
        msg['Subject'] = Header(subject, "utf-8")  # 设置主题
        msg['From'] = self._format_address(sender)
        msg['To'] = ', '.join(self._format_list(recipients))
        msg['Date'] = formatdate()
        # msg["Accept-Language"] = "zh-CN"
        # msg["Accept-Charset"] = "ISO-8859-1,utf-8"

        # 构造MIMEText对象做为邮件显示内容并附加到根容器---邮件正文---
        msg.attach(MIMEText(content, content_type, "utf-8"))
        # 构造MIMEBase对象做为文件附件内容并附加到根容器---邮件附件---
        cid = 0  # 附件序号
        for file_path in file_paths:
            if not os.path.isfile(file_path):
                continue
            file_name = os.path.basename(file_path)
            main_type, sub_type = self._get_file_type(file_name)
            mime = MIMEBase(main_type, sub_type, filename=file_name)
            mime.add_header('Content-Disposition', 'attachment',
                            filename=file_name)  # 设置附件头
            mime.add_header('Content-ID', '<%s>' % cid)
            mime.add_header('X-Attachment-Id', '%s' % cid)
            # 读入文件内容并格式化
            with open(file_path, 'rb') as f:
                mime.set_payload(f.read())
            encode_base64(mime)
            msg.attach(mime)
            cid += 1
            pass

        self.logger.debug('Send mail form %s to %s' % (msg['From'], msg['To']))

        # 初始并连接smtp服务器
        conn_func = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        server = conn_func(host, port, timeout=timeout)
        try:
            # 开启调试模式
            # server.set_debuglevel(1)
            # 如果存在用户名密码则尝试登录
            if username and password:
                server.login(username, password)  # 登陆服务器
            # 发送邮件
            server.sendmail(sender, recipients, msg.as_string().encode("utf8"))
            self.logger.debug('Mail sent success.')
        except socket.gaierror as e:
            # 网络无法连接
            self.logger.exception(e)
            raise NetworkError(e)
        except smtplib.SMTPServerDisconnected as e:
            # 网络连接异常
            self.logger.exception(e)
            raise NetworkError(e)
        except smtplib.SMTPException as e:
            # 邮件发送异常
            self.logger.exception(e)
            raise MailerException(e)
        except Exception as e:
            self.logger.error('{}=>{}'.format(type(e), e))
            raise MailerException(e)
        finally:
            # 关闭stmp连接
            server.quit()
            server.close()
            pass
        pass

    def _format_list(self, address):
        """
        将收件人地址格式化成list
        :param address: string/list 收件人邮箱
        :return: list 收件人邮箱list
        """
        if isinstance(address, (list, tuple)):
            pass
        elif isinstance(address, (str, bytes)):
            address = [address]
        else:
            raise ValueError('E-mail (list) format error! {}'.format(address))
        return [self._format_address(s) for s in address]

    @staticmethod
    def _format_address(s):
        """
        格式化邮件地址
        :param s:string 邮件地址
        :return: string 格式化后的邮件地址
        """
        return formataddr(parseaddr(s))

    @staticmethod
    def _get_file_type(file_name):
        """
        获取附件类型
        :param file_name: 附件文件名
        :return: dict 附件MIME
        """
        s = file_name.lower()
        pos = s.rfind('.')
        if pos == -1:
            return 'application', 'octet-stream'

        ext = s[pos:]
        mime = mimetypes.types_map.get(ext, 'application/octet-stream')
        pos = mime.find('/')
        if pos == (-1):
            return mime, ''
        return mime[:pos], mime[pos + 1:]

    pass


class StopRetry(Exception):
    def __repr__(self):
        return 'retry stop'

    pass


# 异常捕获装饰器（亦可用于类方法）
def try_except_log(f=None, max_retries: int = 5,
                   delay: (int, float) = 1, step: (int, float) = 0,
                   exceptions: (BaseException, tuple, list) = BaseException,
                   sleep=time.sleep, process=None, validate=None, callback=None,
                   default=None):
    """
    函数执行出现异常时自动重试的简单装饰器
    :param f: function 执行的函数。
    :param max_retries: int 最多重试次数。
    :param delay: int/float 每次重试的延迟，单位秒。
    :param step: int/float 每次重试后延迟递增，单位秒。
    :param exceptions: BaseException/tuple/list 触发重试的异常类型，
    单个异常直接传入异常类型，多个异常以tuple或list传入。
    :param sleep: 实现延迟的方法，默认为time.sleep。
    在一些异步框架，如tornado中，使用time.sleep会导致阻塞，可以传入自定义的方法来实现延迟。
    自定义方法函数签名应与time.sleep相同，接收一个参数，为延迟执行的时间。
    :param process: 处理函数，函数签名应接收一个参数，每次出现异常时，会将异常对象传入。
    可用于记录异常日志，中断重试等。
    如处理函数正常执行，并返回True，则表示告知重试装饰器异常已经处理，重试装饰器终止重试，并且不会抛出任何异常。
    如处理函数正常执行，没有返回值或返回除True以外的结果，则继续重试。
    如处理函数抛出异常，则终止重试，并将处理函数的异常抛出。
    :param validate: 验证函数，用于验证执行结果，并确认是否继续重试。
    函数签名应接收一个参数，每次被装饰的函数完成且未抛出任何异常时，调用验证函数，将执行的结果传入。
    如验证函数正常执行，且返回False，则继续重试，即使被装饰的函数完成且未抛出任何异常。
    如验证函数正常执行，没有返回值或返回除False以外的结果，则终止重试，并将函数执行结果返回。
    如验证函数抛出异常，且异常属于被重试装饰器捕获的类型，则继续重试。
    如验证函数抛出异常，且异常不属于被重试装饰器捕获的类型，则将验证函数的异常抛出。
    :param callback: 回调函数，函数签名应接收一个参数，异常无法处理时，会将异常对象传入。
    可用于记录异常日志，发送异常日志等。
    :param default: 默认值/默认值生成函数
    :return: 被装饰函数的执行结果。
    """

    # 带参数的装饰器
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # nonlocal delay, step, max_retries
            i = 0
            func_exc, exc_traceback = StopRetry, None
            while i < max_retries:
                try:
                    result = func(*args, **kwargs)
                    # 验证函数返回False时，表示告知装饰器验证不通过，继续重试
                    if callable(validate) and validate(result) is False:
                        continue
                    else:
                        return result
                except exceptions as ex:
                    func_exc, exc_traceback = ex, traceback.format_exc()
                    # 处理函数返回True时，表示告知装饰器异常已经处理，终止重试
                    if callable(process):
                        try:
                            if process(ex) is True:
                                return default() if callable(
                                    default) else default
                        except Exception as e:
                            func_exc, exc_traceback = e, traceback.format_exc()
                            break
                finally:
                    i += 1
                    sleep(delay + step * i)
            else:
                # 回调函数，处理自动无法处理的异常
                if callable(callback):
                    callback(func_exc, exc_traceback)
                return default() if callable(default) else default
            pass

        return wrapper

    if callable(f):
        return decorator(f)
    return decorator


def test_process(func_ex, logger=None):
    """
    处理函数
    :param func_ex: 异常
    :param logger: 日志实例，用于记录异常日志。
    :return:
    """
    _logger = logger if logger and isinstance(logger,
                                              logging.Logger) else logging
    _logger.warning('{}==>{}'.format(type(func_ex), func_ex))
    pass


def test_callback(func_ex, func, logger=None, msg_queue=None, mailer=None):
    """
    回调函数
    :param func_ex: 函数异常
    :param func: 函数
    :param logger: 日志实例，用于记录异常日志。
    :param msg_queue: 异常信息队列，用于临时存储异常日志以作后续操作，如统一处理。
    :param mailer: 邮件操作实例，用于发送异常日志。
    :return:
    """
    msg = '{}==>{}\r\n{}'.format(type(func_ex), func_ex, traceback.format_exc())
    _logger = logger if logger and isinstance(logger,
                                              logging.Logger) else logging
    _logger.error(msg)
    subject = 'Error from {} at {}'.format(
        func.__name__, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    if msg_queue and isinstance(msg_queue, queue.Queue):
        msg_queue.put((subject, msg))
    if mailer and isinstance(mailer, EmailOperationHelper):
        mailer.send_mail(subject, msg)
    pass


def get_instance(obj, name, inst, inst_type, default=None):
    """
    通过类的self/cls或实例，获取相应类型的实例
    eg.
    _logger = get_instance(self_or_cls, 'logger', logger, logging.Logger,
                           default=logging)
    :param obj: 类的self/cls
    :param name: 实例名称
    :param inst: 默认实例
    :param inst_type: 实例类型
    :param default: 默认值
    :return: 实例
    """
    if obj and hasattr(obj, name) and isinstance(getattr(obj, name), inst_type):
        return getattr(obj, name)
    elif inst and isinstance(inst, inst_type):
        return inst
    else:
        return default
    pass


def get_class_that_defined_method(method):
    """
    通过类函数找到其类
    eg.
    cls_of_func = get_class_that_defined_method(func)
    self_or_cls = None
    if args and cls_of_func and (isinstance(args[0], cls_of_func) or
                                 isinstance(type(args[0]), cls_of_func)):
        self_or_cls = args[0]
    :param method: 类函数
    :return: 类
    """
    # http://stackoverflow.com/a/25959545/3903832
    if inspect.ismethod(method):
        for cls in inspect.getmro(method.__self__.__class__):
            if cls.__dict__.get(method.__name__) is method:
                return cls
        method = method.__func__  # fallback to __qualname__ parsing
    if inspect.isfunction(method):
        cls = getattr(inspect.getmodule(method),
                      method.__qualname__.split('.<locals>', 1)[0].rsplit('.',
                                                                          1)[0])
        if isinstance(cls, type):
            return cls
    # not required since None would have been implicitly returned anyway
    return None


def get_host_ip():
    """
    查询本机ip地址

    # 获取本机计算机名称
    hostname = socket.gethostname()
    # 获取本机ip，有时候获取不到，如没有正确设置主机名称
    ip = socket.gethostbyname(hostname)

    # 在 shell 中可以一行调用，获取到本机IP
    python -c "import socket;print(
    [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in
    [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1])"
    :return: ip
    """

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    s.close()

    return ip


def auth_header(usr, pwd, url=None):
    def _basic_auth_header(username, password):
        auth = "%s:%s" % (username, password)
        if not isinstance(auth, bytes):
            auth = auth.encode('ISO-8859-1')
        return b'Basic ' + urlsafe_b64encode(auth)
        pass

    # 创建认证Authorization
    if usr:
        pwd = pwd if pwd else ''
        return _basic_auth_header(usr, pwd)
    else:  # try netrc
        try:
            host = urlparse(url).hostname
            a = netrc.netrc().authenticators(host)
            return _basic_auth_header(a[0], a[2])
        except (netrc.NetrcParseError, IOError, TypeError):
            pass
    return None
    pass


async def async_http_get(url, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, **kwargs) as response:
            print(time.time())
            return await response.json()
    pass


async def async_http_post(url, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, **kwargs) as response:
            print(time.time())
            return await response.json()
    pass
