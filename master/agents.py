#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/7/4
# @Author: lsj
# @File  : agent.py
# @Desc  : 代理模块
默认Python版本支持：3.6
"""

import datetime
import glob
import json
import logging
import os
import random
import re
import shutil
import time
import traceback
from collections import defaultdict
from distutils.version import LooseVersion
from threading import RLock
from urllib.parse import urljoin

import psutil
import requests
from requests.auth import HTTPBasicAuth

import master.settings as settings
from master.models import JobStatus, JobsModel, JobsExceptionsModel
from master.models import NodesModel, NodesExceptionsModel
from master.models import ProjectsModel, SpidersModel
from master.models import SystemSettingsModel
from master.utils import get_md5

LOCK = RLock()  # 线程锁


class ProxySpider(object):
    """
    Scrapy爬虫操作类，基于scrapyd接口
    # http://scrapyd.readthedocs.io/en/stable/api.html
    """

    def __init__(self, host='localhost', port=6800, username=None, password=''):
        """
        实例化后的初始化函数
        :param host: 域名
        :param port: 端口
        :param username: 用户
        :param password: 密码
        """
        self._base_url = 'http://{}:{}'.format(host, port)
        # 创建认证Authorization
        if username:
            self.auth = HTTPBasicAuth(username, password if password else '')
        else:
            self.auth = None
        pass

    @staticmethod
    def __check_data(json_data):
        """
        检验JSON数据
        :param json_data: JSON数据
        :return:
        """
        if isinstance(json_data, dict) and json_data.get('status') == 'ok':
            return True
        return False
        pass

    def __retry_request(self, action, method='get', retries=5, **kwargs):
        """
        重试请求
        :param action: 链接动作
        :param method: 请求方法 get/post
        :param retries: 重试次数
        :param kwargs: 请求参数 params/data/json/headers/cookies/auth/timeout
                                /proxies/verify
        :return: requests.Response.json()
        """

        url = urljoin(self._base_url, action)
        kwargs["auth"] = self.auth  # 增加请求验证信息
        for i in range(retries):
            try:
                if method == 'get':
                    with requests.get(url, **kwargs) as response:
                        return response.json()
                elif method == 'post':
                    with requests.post(url, **kwargs) as response:
                        return response.json()
                else:
                    raise ValueError(
                        'Unsupported request method:{}'.format(method))
            except Exception as e:
                logging.warning('request error:{}=>{}, retry {}'.format(
                    type(e), e, url))
                # print(traceback.format_exc())
        pass

    # 检查节点状态
    def get_daemon_status(self):
        """
        检查节点状态
        To check the load status of a service.
        curl http://localhost:6800/daemonstatus.json
        curl http://localhost:6800/daemon_status.json
        { "status": "ok", "running": "0", "pending": "0", "finished": "0" }
        :return: True/False
        """
        action = "daemon_status.json"
        json_data = self.__retry_request(action)
        # return True if self.__check_data(json_data) else False
        return json_data
        pass

    # 获取项目列表
    def get_list_projects(self):
        """
        获取项目列表
        Get the list of projects uploaded to this Scrapy server.
        curl http://localhost:6800/listprojects.json
        curl http://localhost:6800/list_projects.json
        {"status": "ok", "projects": ["myProject", "otherProject"]}
        :return: []
        """
        action = "list_projects.json"
        json_data = self.__retry_request(action)
        if self.__check_data(json_data):
            return json_data.get('projects', [])
        return []
        pass

    # 获取项目版本列表
    def get_list_versions(self, project_name):
        """
        获取项目版本列表
        Get the list of versions available for some project.
        The versions are returned in order,
        the last one is the currently used version.
        curl http://localhost:6800/listversions.json?project=myProject
        curl http://localhost:6800/list_versions.json?project=myProject
        {"status": "ok", "versions": ["r99", "r156"]}
        :param project_name: 项目名称
        :return: []
        """
        action = "list_versions.json"
        params = {'project': project_name}
        json_data = self.__retry_request(action, params=params)
        if self.__check_data(json_data):
            return json_data.get('versions', [])
        return []
        pass

    # 获取项目爬虫列表
    def get_list_spiders(self, project_name):
        """
        获取项目爬虫列表
            Get the list of spiders available in the last (unless overridden)
        version of some project.
        curl http://localhost:6800/listspiders.json?project=myProject
        curl http://localhost:6800/list_spiders.json?project=myProject
        {"status": "ok", "spiders": ["spider1", "spider2", "spider3"]}
        :param project_name: 项目名称
        :return: []
        """
        action = "list_spiders.json"
        params = {'project': project_name}
        json_data = self.__retry_request(action, params=params)
        if self.__check_data(json_data):
            return json_data.get('spiders', [])
        return []
        pass

    # 获取项目任务列表
    def get_list_jobs(self, project_name):
        """
        获取项目任务列表
        Get the list of pending, running and finished jobs of some project.
        curl http://localhost:6800/listjobs.json?project=myProject
        curl http://localhost:6800/list_jobs.json?project=myProject
        {"status": "ok", "pending": [], "running": [], "finished": []}
        :param project_name: 项目名称
        :return: {}
        """
        action = "list_jobs.json"
        params = {'project': project_name}
        json_data = self.__retry_request(action, params=params)
        if self.__check_data(json_data):
            # '%Y-%m-%d %H:%M:%S.%f'  2012-09-12 10:24:03.594664
            return {
                'pending': json_data.get("pending", []),
                'running': json_data.get("running", []),
                'finished': json_data.get("finished", []),
            }
        return {}
        pass

    # 删除项目
    def del_project(self, project_name):
        """
        删除项目
        Delete a project and all its uploaded versions.
        curl http://localhost:6800/delproject.json -d project=myProject
        curl http://localhost:6800/del_project.json -d project=myProject
        {"status": "ok"}
        :param project_name: 项目名称
        :return: True/False
        """
        action = "del_project.json"
        data = {'project': project_name}
        json_data = self.__retry_request(action, method='post', data=data)
        return True if self.__check_data(json_data) else False

    # 删除项目版本
    def del_version(self, project_name, version_name):
        """
        删除项目版本
        Delete a project version.
        If there are no more versions available for a given project,
        that project will be deleted too.
        curl http://localhost:6800/delversion.json -d project=my -d version=r99
        curl http://localhost:6800/del_version.json -d project=my -d version=r99
        {"status": "ok"}
        :param project_name: 项目名称
        :param version_name: 版本名称
        :return: True/False
        """
        action = "del_version.json"
        data = {'project': project_name, 'version': version_name}
        json_data = self.__retry_request(action, method='post', data=data)
        return True if self.__check_data(json_data) else False

    # 启动爬虫
    def start_spider(self, project_name, spider_name, **kwargs):
        """
        启动爬虫
        Schedule a spider run (also known as a job), returning the job id.
        curl http://localhost:6800/schedule.json -d project=my -d spider=some
        {"status": "ok", "jobid": "6487ec79947edab326d6db28a2d86511e8247444"}
        :param project_name: 项目名称
        :param spider_name: 爬虫名称
        :param kwargs: 爬虫参数
        :return:
        """
        action = "schedule.json"
        data = {'project': project_name, 'spider': spider_name}
        data.update(kwargs)
        json_data = self.__retry_request(action, method='post', data=data)
        return json_data.get('job') if self.__check_data(json_data) else None

    # 终止爬虫
    def cancel_spider(self, project_name, job_id):
        """
        终止爬虫
        Cancel a spider run (aka. job).
        If the job is pending, it will be removed.
        If the job is running, it will be terminated.
        curl http://localhost:6800/cancel.json -d project=my -d job=6487
        {"status": "ok", "prev_state": "running"}
        :param project_name: 项目名称
        :param job_id: 爬虫运行ID
        :return: True/False
        """
        action = "cancel.json"
        data = {'project': project_name, 'job': job_id}
        json_data = self.__retry_request(action, method='post', data=data)
        return True if self.__check_data(json_data) else False

    # 部署项目
    def deploy_project(self, egg_data, project_name, version_name=None):
        """
        Add a version to a project, creating the project if it does not exist.
        curl http://localhost:6800/addversion.json -F project=my -F version=r23 -F egg=@myproject.egg
        {"status": "ok", "spiders": 3}
        :param egg_data: EGG文件数据
        :param project_name: 项目名称
        :param version_name: 版本名称
        :return:
        """
        action = "add_version.json"
        data = {
            'project': project_name,
            'version': version_name if version_name else str(int(time.time())),
            'egg': egg_data,
        }
        json_data = self.__retry_request(action, method='post', data=data)
        return True if self.__check_data(json_data) else False

    def get_job_exception(self, project_name, spider_name, job_id, offset=0):
        action = "job_exception.json"
        params = {
            "project": project_name,
            "spider": spider_name,
            "job": job_id,
            "offset": offset,
        }
        json_data = self.__retry_request(action, method='post', params=params)
        if self.__check_data(json_data):
            return json_data.get('whence', 0), json_data.get('errors', [])
        return 0, []
        pass

    def get_sys_performance(self):
        action = "sys_performance.json"
        json_data = self.__retry_request(action)
        if self.__check_data(json_data):
            return json_data.get('performance', [])
        return []
        pass

    # 运行日志网络路径
    def log_url(self, project_name, spider_name, job_id):
        """
        运行日志网络路径
        :param project_name: 项目名称
        :param spider_name: 爬虫名称
        :param job_id: 爬虫运行ID
        :return:
        """
        return self._base_url + '/logs/%s/%s/%s.log' % (
            project_name, spider_name, job_id)

    pass


class FilesystemEggStorage(object):

    def __init__(self, eggs_dir="eggs"):
        self.basedir = eggs_dir

    @property
    def projects(self):
        return os.listdir(self.basedir) if os.path.exists(self.basedir) else []

    def put(self, egg_file, project, version):
        egg_path = self._egg_path(project, version)
        egg_dir = os.path.dirname(egg_path)
        if not os.path.exists(egg_dir):
            os.makedirs(egg_dir)
        with open(egg_path, 'wb') as f:
            shutil.copyfileobj(egg_file, f)

    def get(self, project, version=None):
        if version is None:
            try:
                version = self.list(project)[-1]
            except IndexError:
                return None, None
        return version, open(self._egg_path(project, version), 'rb')

    def list(self, project):
        egg_dir = os.path.join(self.basedir, project)
        versions = [os.path.splitext(os.path.basename(x))[0] for x in
                    glob.glob("%s/*.egg" % egg_dir)]
        return sorted(versions, key=LooseVersion)

    def delete(self, project, version=None):
        if version is None:
            shutil.rmtree(os.path.join(self.basedir, project))
        else:
            os.remove(self._egg_path(project, version))
            if not self.list(project):  # remove project if no versions left
                self.delete(project)

    def _egg_path(self, project, version):
        sanitized_version = re.sub(r'[^a-zA-Z0-9_-]', '_', version)
        x = os.path.join(self.basedir, project, "%s.egg" % sanitized_version)
        return x

    pass


'''========= Agent ========='''


# 爬虫代理类
class SpiderAgent(object):

    def __init__(self):
        """初始函数"""
        self.egg_storage = FilesystemEggStorage(settings.DIR_EGGS)
        self.proxies = {}  # 节点代理字典
        self.slaves = {}  # 节点字典
        self.projects = {}  # 项目字典

        # system performance indicators
        self.disk_io_read_speed = None
        self.disk_io_write_speed = None
        self.net_io_sent_speed = None
        self.net_io_receive_speed = None
        self._last_time = None
        # Disk I/O
        self._last_disk_io_read_bytes = None
        self._last_disk_io_write_bytes = None
        # Net I/O
        self._last_net_io_sent_bytes = None
        self._last_net_io_receive_bytes = None
        pass

    def register(self):
        """
        注册
        projects = {
            "p1": {
                "v1": ["s1", "s2", "s3"],
                "v2": [],
            },
            "p2": {},
        }
        :return:
        """
        # register spider service proxy 注册
        for n in NodesModel.get_list(node_type="slave"):
            self.merge_client(n.host_port, n.username, n.password)

        # 获取本地projects列表
        models = ProjectsModel.get_list()
        models = {m.project_name: m.get_versions_spiders() for m in models}
        for project_name in self.egg_storage.projects:
            versions = self.egg_storage.list(project_name)
            if not versions:
                continue
            self.projects[project_name] = {
                v: models.get(project_name, {}).get(v, []) for v in
                versions}
            ProjectsModel.merge_one(
                project_name=project_name,
                version_name=versions[0],
                versions=json.dumps(versions),
            )
        pass

    def get_salve_performance(self, host_port):
        """获取从节点性能指数"""
        proxies_detail = self.proxies.get(host_port, {})
        if proxies_detail.get("status"):
            instance = proxies_detail.get("instance")
            if isinstance(instance, ProxySpider):
                return instance.get_sys_performance()
        return {}
        pass

    def get_master_performance(self):
        """获取主节点性能指数"""
        return {
            'cpu': psutil.cpu_percent(),
            'virtual_memory': psutil.virtual_memory().percent,
            'swap_memory': psutil.swap_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'disk_io_read': self.disk_io_read_speed,
            'disk_io_write': self.disk_io_write_speed,
            'net_io_sent': self.net_io_sent_speed,
            'net_io_receive': self.net_io_receive_speed,
        }
        pass

    def get_default_version(self, project_name):
        versions = self.egg_storage.list(project_name)
        return str(versions[0]) if versions else None
        pass

    def poll_system_performance(self):
        """
        轮询函数，计算本地磁盘IO读写速度及网络IO收发速度
        :return:
        """
        curr_time = time.time()  # 当前时间
        disk_io = psutil.disk_io_counters()  # 磁盘IO状态
        net_io = psutil.net_io_counters()  # 网络IO状态

        timedelta = curr_time - self._last_time if self._last_time else None
        if timedelta:
            # 分母 单位：KB/s
            denominator = 1024 * timedelta
            read_bytes = disk_io.read_bytes - self._last_disk_io_read_bytes
            write_bytes = disk_io.write_bytes - self._last_disk_io_write_bytes
            self.disk_io_read_speed = round(read_bytes / denominator, 2)
            self.disk_io_write_speed = round(write_bytes / denominator, 2)
            # 分母 单位：Kb/s
            denominator = 1000 * timedelta
            sent_bytes = net_io.bytes_sent - self._last_net_io_sent_bytes
            receive_bytes = net_io.bytes_recv - self._last_net_io_receive_bytes
            self.net_io_sent_speed = round(sent_bytes / denominator, 2)
            self.net_io_receive_speed = round(receive_bytes / denominator, 2)

        self._last_time = curr_time
        self._last_disk_io_read_bytes = disk_io.read_bytes
        self._last_disk_io_write_bytes = disk_io.write_bytes
        self._last_net_io_sent_bytes = net_io.bytes_sent
        self._last_net_io_receive_bytes = net_io.bytes_recv

        pass

    def load_balance(self):
        """负载均衡函数"""
        pass

    def set_slaves_value(self, slave_name, project_name=None, *version_names):
        if not slave_name:
            return
        if slave_name not in self.slaves:
            self.slaves[slave_name] = {}
        if not project_name:
            return
        if project_name not in self.slaves[slave_name]:
            self.slaves[slave_name][project_name] = set()
        if not version_names:
            return
        self.slaves[slave_name][project_name].update(set(version_names))
        pass

    def del_slaves_value(self, slave_name, project_name=None, *version_names):
        self.set_slaves_value(slave_name, project_name)
        if version_names:
            versions = self.slaves[slave_name][project_name]
            for version_name in set(version_names).intersection(versions):
                versions.remove(version_name)
            if not versions:
                self.slaves[slave_name].pop(project_name)
            return
        if project_name:
            self.slaves[slave_name].pop(project_name)
            return
        if slave_name:
            self.slaves.pop(slave_name)
        pass

    # 添加/修改节点
    def merge_client(self, host_port, username=None, password=''):
        """
        添加节点
        :param host_port: 节点地址，例如"localhost:6800"
        :param username: 用户
        :param password: 密码
        :return:
        """
        host, port = host_port.split(":")
        # 创建爬虫代理操作实例
        instance = ProxySpider(
            host=host, port=port, username=username, password=password)
        slave_name = host_port
        if host_port in self.proxies:
            self.proxies[host_port]["instance"] = instance
        else:
            self.proxies[host_port] = {
                "status": False,
                "instance": instance,
            }
        self.set_slaves_value(slave_name)
        pass

    # 删除节点
    def delete_client(self, host_port):
        """
        删除节点
        :param host_port: 节点地址，例如"localhost:6800"
        :return:
        """
        slave_name = host_port
        self.del_slaves_value(slave_name)
        if slave_name in self.proxies:
            del self.proxies[slave_name]
        pass

    # 发布项目
    def deploy_project(self, egg_file, project_name, version_name=None):
        """
        发布项目
        :param egg_file: 蛇蛋文件
        :param project_name: 项目名称
        :param version_name: 版本名称，默认时间戳
        :return:
        """
        version_name = version_name if version_name else str(int(time.time()))
        self.egg_storage.put(egg_file, project_name, version_name)
        _, egg_file = self.egg_storage.get(project_name, version_name)
        versions = self.egg_storage.list(project_name)  # 版本列表
        with egg_file as f:  # with open(file_path, 'rb') as f:
            egg_data = f.read()
        spiders = []  # 爬虫列表
        for slave_name, proxies_detail in self.proxies.items():
            if not proxies_detail.get("status"):
                continue
            instance = proxies_detail.get("instance")
            if not isinstance(instance, ProxySpider):
                continue
            flag = instance.deploy_project(egg_data, project_name, version_name)
            if flag:
                self.set_slaves_value(slave_name, project_name, version_name)
            if not spiders:
                spiders = instance.get_list_spiders(project_name)
            pass

        default_version = versions[0]  # 默认版本
        if project_name not in self.projects:
            self.projects[project_name] = {v: [] for v in versions}
        self.projects[project_name][default_version] = spiders
        ProjectsModel.merge_one(
            project_name=project_name,
            version_name=versions[0],
            versions=json.dumps(versions),
        )
        SpidersModel.sync_spiders(project_name, default_version, *spiders)
        return True
        pass

    # 删除项目
    def delete_project(self, project_name, version_name=None):
        """
        删除项目
        :param project_name: 项目名称
        :param version_name: 版本名称
        :return:
        """
        for slave_name, proxies_detail in self.proxies.items():
            if not proxies_detail.get("status"):
                continue
            instance = proxies_detail.get("instance")
            if not isinstance(instance, ProxySpider):
                continue
            if version_name:
                instance.del_version(project_name, version_name)
                self.del_slaves_value(slave_name, project_name, version_name)
            else:
                instance.del_project(project_name)
                self.del_slaves_value(slave_name, project_name)
            pass
        try:
            self.egg_storage.delete(project_name, version_name)
        except Exception as e:
            print(e)
        versions = self.egg_storage.list(project_name)
        if versions:
            default_version = versions[0]
            if project_name in self.projects:
                if version_name in self.projects[project_name]:
                    self.projects[project_name].pop(version_name)
            SpidersModel.del_many(
                version_name=version_name, project_name=project_name)
            ProjectsModel.merge_one(
                project_name=project_name,
                version_name=default_version,
                versions=json.dumps(versions),
            )
        else:
            if project_name in self.projects:
                self.projects.pop(project_name)
            SpidersModel.del_many(project_name=project_name)
            ProjectsModel.del_one(vc_md5=get_md5(project_name))
        pass

    # 开启爬虫
    def start_spider(self, project_name, spider_name,
                     version_name=None, exec_args=None,
                     host_port=None, plan_name=None, **kwargs):
        # 爬虫运行参数
        arguments = defaultdict(list)
        if kwargs.get("spider_setting"):
            arguments["setting"] = kwargs.get("spider_setting")
        if kwargs.get("job_id"):
            arguments["job"] = kwargs.get("job_id")
        if not version_name:
            version_name = self.get_default_version(project_name)
        if version_name:
            arguments["_version"] = version_name
        if exec_args:
            for k, v in list(map(
                    lambda x: x.split('=', 1), exec_args.split(','))):
                arguments[k].append(v)
        # 选择运行节点
        client_list = [k for k, v in self.proxies.items() if v.get("status")]
        if client_list and (not host_port or host_port == "auto"
                            or host_port not in client_list):
            host_port = random.choice(client_list)
        if not host_port:
            return
        instance = self.proxies.get(host_port, {}).get("instance")
        if not isinstance(instance, ProxySpider):
            return
        # 运行爬虫
        job_id = instance.start_spider(project_name, spider_name, **arguments)
        JobsModel.merge_one(
            plan_name=plan_name,
            host_port=host_port,
            project_name=project_name,
            version_name=version_name,
            spider_name=spider_name,
            job_id=job_id,
            create_time=datetime.datetime.now(),
            job_status=JobStatus.PENDING.value,
        )
        return job_id
        pass

    # 终止爬虫
    def cancel_spider(self, host_port, project_name, job_id):
        proxies_detail = self.proxies.get(host_port, {})
        if not proxies_detail.get("status"):
            return
        instance = proxies_detail.get("instance")
        if not isinstance(instance, ProxySpider):
            return
        if instance.cancel_spider(project_name, job_id):
            JobsModel.update_one(
                vc_md5=get_md5(host_port, project_name, job_id),
                end_time=datetime.datetime.now(),
                job_status=JobStatus.CANCELED.value)
            return True
        pass

    # 爬虫日志网络路径
    def log_url(self, host_port, project_name, spider_name, job_id):
        instance = self.proxies.get(host_port, {}).get("instance")
        if not isinstance(instance, ProxySpider):
            return
        return instance.log_url(project_name, spider_name, job_id)
        pass

    # 同步节点状态
    def sync_slaves_status(self):
        """
        检查运行节点
        :return:
        """
        for host_port, proxies_detail in self.proxies.items():
            instance = proxies_detail.get("instance")
            if not isinstance(instance, ProxySpider):
                continue
            daemon_status = instance.get_daemon_status() or {}
            status = daemon_status.get("status", False)
            proxies_detail["status"] = status
            NodesModel.update_one(
                vc_md5=get_md5(host_port),
                node_name=daemon_status.get("node_name", False),
                status='运行正常' if status else "链接失败",
                pending=daemon_status.get("pending"),
                running=daemon_status.get("running"),
                finished=daemon_status.get("finished")
            )
        pass

    # 同步节点异常（性能指标）
    def sync_nodes_exception(self):
        """同步节点异常（性能指标）"""
        system_settings = SystemSettingsModel.get_settings()
        # Master
        for key, value in self.get_master_performance().items():
            threshold = system_settings.get("threshold_{}".format(key))
            if not threshold or threshold > value:
                continue
            NodesExceptionsModel.merge_one(
                host_port="Master",
                node_type="master",
                exc_time=datetime.datetime.now(),
                exc_level="WARNING",
                exc_message="Current {} is {}(>={})!".format(
                    key, value, threshold)
            )
            pass
        # Slave
        for host_port in self.slaves:
            for key, value in self.get_salve_performance(host_port).items():
                threshold = system_settings.get("threshold_{}".format(key))
                if not threshold or threshold > value:
                    continue
                NodesExceptionsModel.merge_one(
                    host_port=host_port,
                    node_type="slave",
                    exc_time=datetime.datetime.now(),
                    exc_level="WARNING",
                    exc_message="Current {} is {}(>={})!".format(
                        key, value, threshold)
                )
                pass
        pass

    # 同步项目部署
    def sync_projects_list(self):
        """
        同步项目(初始化执行或手动执行)
        :return:
        """
        for project_name, project_detail in self.projects.items():
            for version_name, version_detail in project_detail.items():
                # spiders = version_detail.get("spiders", [])
                # slaves = version_detail.get("slaves", set())
                _, egg_file = self.egg_storage.get(project_name, version_name)
                with egg_file as f:  # with open(file_path, 'rb') as f:
                    egg_data = f.read()
                for slave_name, proxies_detail in self.proxies.items():
                    # 若节点异常
                    if not proxies_detail.get("status"):
                        continue
                    instance = proxies_detail.get("instance")
                    if not isinstance(instance, ProxySpider):
                        continue
                    if not version_detail:
                        spiders = instance.get_list_spiders(project_name)
                        if spiders:
                            # set().update(set())
                            version_detail.update(set(spiders))
                            SpidersModel.sync_spiders(
                                project_name, version_name, *spiders)
                    # 若未部署,重新部署
                    if version_name in self.slaves.get(slave_name, {}).get(
                            project_name, set()):
                        continue
                    if not instance.deploy_project(
                            egg_data, project_name, version_name):
                        continue
                    self.set_slaves_value(slave_name, project_name,
                                          version_name)
                    pass
            pass
        pass

    # 同步任务任务
    def sync_jobs_status(self):
        """
        同步任务执行状态JobsStatus
        :return:
        """
        for host_port, proxies_detail in self.proxies.items():
            if not proxies_detail.get("status"):
                continue
            instance = proxies_detail.get("instance")
            if not isinstance(instance, ProxySpider):
                continue
            for project_name in self.projects:
                jobs = instance.get_list_jobs(project_name)
                for job_status, jobs_detail in jobs.items():
                    for job_detail in jobs_detail:
                        start_time = job_detail.get('start_time')
                        start_time = self.str_to_time(start_time)
                        end_time = job_detail.get('end_time')
                        end_time = self.str_to_time(end_time)
                        running_time = self.time_difference(
                            start_time, end_time)
                        JobsModel.merge_one(
                            job_id=job_detail.get('id'),
                            host_port=host_port,
                            project_name=project_name,
                            spider_name=job_detail.get('spider'),
                            start_time=start_time,
                            end_time=end_time,
                            running_time=running_time,
                            job_status=job_status)
            pass
        pass

    def sync_jobs_exception(self):
        result = {}
        for model in JobsModel.get_jobs_retrieving():
            host_port = model.host_port
            if host_port not in result:
                result[host_port] = []
            result[host_port].append(model)
        for host_port, models in result.items():
            if host_port not in self.proxies:
                continue
            proxies_detail = self.proxies.get(host_port, {})
            if not proxies_detail.get("status"):
                continue
            instance = proxies_detail.get("instance")
            if not isinstance(instance, ProxySpider):
                continue
            for model in models:
                whence, errors = instance.get_job_exception(
                    project_name=model.project_name,
                    spider_name=model.spider_name,
                    job_id=model.job_id,
                    offset=model.log_progress or 0
                )
                # if not whence:
                #     continue
                log_status = 0 if model.job_status == JobStatus.RUNNING else 1
                for (exc_time, exc_level, exc_message) in errors:
                    JobsExceptionsModel.merge_one(
                        host_port=model.host_port,
                        project_name=model.project_name,
                        version_name=model.version_name,
                        spider_name=model.spider_name,
                        plan_name=model.plan_name,
                        job_id=model.job_id,
                        exc_time=exc_time,
                        exc_level=exc_level,
                        exc_message=exc_message
                    )
                    pass
                JobsModel.update_one(
                    model=model,
                    log_status=log_status,
                    log_progress=whence
                )
            pass
        pass

    @property
    def servers(self):
        return self.proxies.keys()
        pass

    @staticmethod
    def str_to_time(string):
        if not string:
            return
        return datetime.datetime.strptime(string, '%Y-%m-%d %H:%M:%S.%f')
        pass

    @staticmethod
    def time_difference(t1, t2):
        if not t1 or not t2:
            return
        return int(time.mktime(t2.timetuple()) - time.mktime(t1.timetuple()))
        pass

    pass


# 代理
agent = SpiderAgent()


# 注册服务
def register_server():
    agent.register()
    pass
