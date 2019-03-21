#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import hashlib
import json
from enum import Enum

from flask import current_app
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash

from master.utils import get_md5
from master.utils import seconds2time, datetime2str, time_difference

db = SQLAlchemy(session_options=dict(autocommit=False, autoflush=True))


class BaseModel(db.Model):
    __abstract__ = True  # 扩充模型的基类
    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'}

    dt_create = db.Column(
        "dt_create", db.TIMESTAMP,
        default=db.func.current_timestamp(), comment="创建时间")
    dt_update = db.Column(
        "dt_update", db.TIMESTAMP,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(), comment="更新时间")
    vc_md5 = db.Column(
        "vc_md5", db.String(100), primary_key=True, comment="去重标识")

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        pass

    @property
    def id(self):
        return self.vc_md5
        pass

    def to_dict(self):
        return dict(
            dt_create=self.dt_create,
            dt_update=self.dt_update,
            vc_md5=self.vc_md5,
        )
        pass

    @classmethod
    def __get_query(cls, *args, **kwargs):
        query = cls.query
        if args:
            query = query.filter(cls.vc_md5.in_(args))
        if "keywords" in kwargs:
            keywords = kwargs.pop('keywords')
            columns = ['host_port', 'project_name', 'spider_name',
                       'plan_name', 'job_id',
                       'exc_level', 'exc_message', 'remark']
            columns = [getattr(cls, c) for c in columns if hasattr(cls, c)]
            if columns:
                query = query.filter(db.or_(*[
                    c.like('%{}%'.format(keywords)) for c in columns]))
        if kwargs:
            query = query.filter_by(**kwargs)
        # return query.order_by(cls.dt_update.desc())
        return query
        pass

    @classmethod
    def get_first(cls, *args, **kwargs):
        """
        获取符合条件的首条数据
        :param kwargs: 查询条件
        :return:
        """
        query = cls.__get_query(*args, **kwargs)
        return query.first()
        pass

    @classmethod
    def get_list(cls, *args, **kwargs):
        """
        获取符合条件的数据
        :param kwargs: 查询条件
        :return: []
        """
        query = cls.__get_query(*args, **kwargs)
        return query.all()
        pass

    @classmethod
    def get_dicts(cls, *args, **kwargs):
        """
        获取符合条件的数据
        :param args: 查询条件
        :param kwargs: 查询条件
        :return: []
        """
        query = cls.__get_query(*args, **kwargs)
        models = query.all()
        return [model.to_dict() for model in models] if models else []
        pass

    @classmethod
    def get_limit(cls, limit=10, *args, **kwargs):
        """
        获取符合条件的前N条数据
        :param limit: 获取数据条数限制，如前N条
        :param kwargs: 查询条件
        :return: []
        """
        query = cls.__get_query(*args, **kwargs).limit(limit)
        return query.all()
        pass

    @classmethod
    def get_pagination(cls, page_index=1, page_size=10, *args, **kwargs):
        """
        获取分页数据
        :param page_index: 页码
        :param page_size: 每页数量
        :param args: 查询条件
        :param kwargs: 查询条件
        :return: {}
        """
        query = cls.__get_query(*args, **kwargs)
        pagination = query.paginate(int(page_index), int(page_size), False)
        return dict(
            has_prev=pagination.has_prev,
            iter_pages=list(pagination.iter_pages()),
            page=pagination.page,
            pages=pagination.pages,
            has_next=pagination.has_next,
            items=[m.to_dict() for m in
                   pagination.items] if pagination.items else []
        ) if pagination else {}
        pass

    @classmethod
    def merge_one(cls, **kwargs):
        """
        新增或更新
        :param kwargs: 数据项
        :return:
        """
        model = cls(**kwargs)
        db.session.merge(model)
        db.session.commit()
        return model
        pass

    @classmethod
    def update_one(cls, vc_md5=None, model=None, **kwargs):
        # cls.query.filter(cls.vc_md5 == vc_md5).update(kwargs)
        if vc_md5:
            model = cls.get_first(vc_md5=vc_md5)
        if model:
            for k, v in kwargs.items():
                if hasattr(model, k):
                    setattr(model, k, v)
            db.session.commit()
        pass

    @classmethod
    def update_many(cls, *args, **kwargs):
        query = cls.query
        if args:
            query = query.filter(cls.vc_md5.in_(args))
        kws = {getattr(cls, k): v for k, v in kwargs.items() if hasattr(cls, k)}
        if kws:
            query.update(kws, synchronize_session=False)
            db.session.commit()
        pass

    @classmethod
    def del_one(cls, *args, **kwargs):
        """
        删除符合条件的第一条数据，并返回该数据
        :param kwargs: 查询条件
        :return:
        """
        model = cls.get_first(*args, **kwargs)
        if model:
            db.session.delete(model)
            db.session.commit()
        return model
        pass

    @classmethod
    def del_many(cls, *args, **kwargs):
        """
        删除符合条件的数据
        :param args: 查询条件
        :param kwargs: 查询条件
        :return:
        """
        # update和delete在做批量操作的时候（使用 where…in(…)）操作，需要指定synchronize_session的值
        query = cls.__get_query(*args, **kwargs)
        query.delete(synchronize_session=False)
        db.session.commit()
        pass

    pass


class NodesModel(BaseModel):
    """主机管理"""
    __tablename__ = 'sp_nodes'

    # vc_md5 主键，MD5值，md5(host_port)
    host_port = db.Column(db.String(100), nullable=False, comment="域名端口")
    group_name = db.Column(db.String(100), comment="分组名称")
    node_name = db.Column(db.String(100), comment="节点名称")
    node_type = db.Column(db.String(100), default="slave", comment="节点类型")
    username = db.Column(db.String(100), comment="节点用户")
    password = db.Column(db.String(100), comment="节点密码")
    status = db.Column(db.String(100), comment="节点状态")
    pending = db.Column(db.String(100), comment="等待中")
    running = db.Column(db.String(100), comment="运行中")
    finished = db.Column(db.String(100), comment="已结束")
    recipients = db.Column(db.String(1000), comment="异常收件")

    jobs = db.relationship("JobsModel", back_populates="node")
    exceptions = db.relationship("NodesExceptionsModel", back_populates="node")

    def __init__(self, host_port=None, **kwargs):
        super().__init__(**kwargs)
        if host_port:
            self.vc_md5 = get_md5(host_port)
            self.host_port = host_port
        pass

    def to_dict(self):
        return {
            "vc_md5": self.vc_md5,
            "host_port": self.host_port,
            "group_name": self.group_name,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "username": self.username,
            "password": self.password,
            "status": self.status,
            "pending": self.pending,
            "running": self.running,
            "finished": self.finished,
            "recipients": self.recipients,
        }
        pass

    @classmethod
    def init_master(cls):
        master = cls(host_port="Master", group_name="master",
                     node_type="master")
        db.session.merge(master)
        db.session.commit()
        pass

    pass


class NodesExceptionsModel(BaseModel):
    """运行异常"""
    __tablename__ = 'sp_nodes_exceptions'

    node_md5 = db.Column(
        db.String(100), db.ForeignKey('sp_nodes.vc_md5'), comment="节点MD5")

    # vc_md5 主键，MD5值，md5(host_port#exc_time)
    host_port = db.Column(db.String(100), nullable=False, comment='节点名称')
    node_type = db.Column(db.String(100), default="slave", comment="节点类型")
    exc_time = db.Column(db.DateTime, nullable=False, comment='异常时间')
    exc_level = db.Column(db.String(100), comment='异常等级')
    exc_message = db.Column(db.Text, comment='异常信息')
    remark = db.Column(db.Text, comment='备注')
    is_closed = db.Column(db.Boolean, default=False, comment='是否关闭')
    is_emailed = db.Column(
        db.Boolean, default=False, comment='是否邮件；0：未发送；1：已发送')

    node = db.relationship("NodesModel", back_populates="exceptions")

    def __init__(self, host_port=None, exc_time=None, **kwargs):
        super().__init__(**kwargs)
        if exc_time and isinstance(exc_time, str):
            exc_time = datetime.datetime.strptime(exc_time, '%Y-%m-%d %H:%M:%S')
        if host_port:
            if exc_time:
                self.vc_md5 = get_md5(
                    host_port, exc_time.strftime('%Y-%m-%d %H:%M:%S'))
            self.node_md5 = get_md5(host_port)
            self.host_port = host_port
        if exc_time:
            self.exc_time = exc_time
        pass

    def to_dict(self):
        return {
            "vc_md5": self.vc_md5,
            "host_port": self.host_port,
            "node_type": self.node_type,
            "exc_time": datetime2str(self.exc_time),
            "exc_level": self.exc_level,
            "exc_message": self.exc_message,
            "remark": self.remark,
            "is_closed": self.is_closed,
            "is_emailed": self.is_emailed,
        }
        pass

    def get_email_content(self):
        s = ""
        s += "Salve: {}\r\n".format(self.host_port)
        s += "Type: {}\r\n".format(self.node_type)
        s += "ExcTime: {}\r\n".format(self.exc_time)
        s += "ExcLevel: {}\r\n".format(self.exc_level)
        s += "ExcMessage: {}\r\n".format(self.exc_message)
        s += "Remark: {}\r\n".format(self.remark)
        return s
        pass

    pass


class ProjectsModel(BaseModel):
    """项目管理"""
    __tablename__ = 'sp_projects'

    # vc_md5 主键，MD5值，md5(project_name)
    project_name = db.Column(db.String(100), nullable=False, comment='项目名称')
    version_name = db.Column(db.String(100), comment='版本名称')
    versions = db.Column(db.String(1000), comment='版本列表')
    recipients = db.Column(db.String(1000), comment="异常收件")

    spiders = db.relationship("SpidersModel", back_populates="project")
    plans = db.relationship("PlansModel", back_populates="project")
    jobs = db.relationship("JobsModel", back_populates="project")

    def __init__(self, project_name=None, **kwargs):
        super().__init__(**kwargs)
        if project_name:
            self.vc_md5 = get_md5(project_name)
            self.project_name = project_name
        pass

    def to_dict(self):
        return {
            "vc_md5": self.vc_md5,
            "project_name": self.project_name,
            "version_name": self.version_name,
            "versions": json.loads(self.versions) or [],
            "recipients": self.recipients,
            "spiders": self.get_spiders(),
        }
        pass

    def get_versions_spiders(self, version_name=None):
        if not self.versions:
            return {}
        versions = json.loads(self.versions)
        if version_name and version_name in versions:
            versions = [version_name]
        versions = {v: [] for v in versions}
        for s in self.spiders:
            if s.version_name in versions:
                versions[s.version_name].append(s.spider_name)
        return versions
        pass

    def get_versions(self):
        if not self.versions:
            return []
        tmp = dict()
        for s in self.spiders:
            version_name = s.version_name
            if version_name not in tmp:
                tmp[version_name] = []
            tmp[version_name].append(s.to_dict())
        return [{
            "vc_md5": get_md5(self.project_name, v),
            "project_name": self.project_name,
            "version_name": v,
            "spiders": tmp.get(v, []), } for v in json.loads(self.versions)]
        pass

    def get_spiders(self, version_name=None):
        return [s.spider_name for s in SpidersModel.get_list(
            version_name=version_name or self.version_name,
            project_name=self.project_name)]
        pass

    pass


class SpidersModel(BaseModel):
    """
    爬虫管理
    $ curl http://localhost:6800/listspiders.json?project=myproject
    {"status": "ok", "spiders": ["spider1", "spider2", "spider3"]}
    """
    __tablename__ = 'sp_spiders'

    project_md5 = db.Column(
        db.String(100), db.ForeignKey('sp_projects.vc_md5'), comment="项目MD5")

    # vc_md5 主键，MD5值，md5(project_name#version_name#spider_name)
    project_name = db.Column(db.String(100), nullable=False, comment='项目名称')
    version_name = db.Column(db.String(100), nullable=False, comment='版本名称')
    spider_name = db.Column(db.String(100), nullable=False, comment='爬虫名称')

    start_time_last = db.Column(db.DateTime, comment='开始时间（最近）')
    waiting_time_avg = db.Column(db.Float, comment='等待时间（平均，秒）')
    running_time_avg = db.Column(db.Float, comment='运行时间（平均，秒）')
    runs_num = db.Column(db.Integer, default=0, comment='运行次数')

    project = db.relationship("ProjectsModel", back_populates="spiders")
    plans = db.relationship("PlansModel", back_populates="spider")
    jobs = db.relationship("JobsModel", back_populates="spider")

    def __init__(self, project_name=None, version_name=None, spider_name=None,
                 **kwargs):
        super().__init__(**kwargs)
        if project_name and version_name and spider_name:
            self.vc_md5 = get_md5(project_name, version_name, spider_name)
        if project_name:
            self.project_name = project_name
        if version_name:
            self.version_name = version_name
        if spider_name:
            self.spider_name = spider_name
        pass

    def to_dict(self):
        return {
            "vc_md5": self.vc_md5,
            "project_name": self.project_name,
            "version_name": self.version_name,
            "spider_name": self.spider_name,
            "start_time_last": datetime2str(self.start_time_last),
            "waiting_time_avg": seconds2time(self.waiting_time_avg),
            "running_time_avg": seconds2time(self.running_time_avg),
            "runs_num": self.runs_num,
        }

    @classmethod
    def sync_spiders(cls, project_name, version_name, *spider_names):
        md5_set = set()
        # 新增或更新 add
        for spider_name in spider_names:
            model = cls(project_md5=get_md5(project_name),
                        project_name=project_name,
                        version_name=version_name,
                        spider_name=spider_name)
            md5_set.add(model.vc_md5)
            db.session.merge(model)
            db.session.commit()
        # 删除 synchronize_session=False
        query = cls.query.filter(cls.vc_md5.notin_(md5_set),
                                 cls.version_name == version_name,
                                 cls.project_name == project_name)
        query.delete(synchronize_session=False)
        db.session.commit()
        pass

    pass


class PlansModel(BaseModel):
    """任务管理"""
    __tablename__ = 'sp_plans'

    project_md5 = db.Column(
        db.String(100), db.ForeignKey('sp_projects.vc_md5'), comment="项目MD5")
    spider_md5 = db.Column(
        db.String(100), db.ForeignKey('sp_spiders.vc_md5'), comment="爬虫MD5")

    # vc_md5 主键，MD5值，md5(plan_name)
    plan_name = db.Column(db.String(100), nullable=False, comment='计划名称')
    project_name = db.Column(db.String(100), comment='项目名称')
    version_name = db.Column(db.String(100), comment='版本名称')
    spider_name = db.Column(db.String(100), comment='爬虫名称')
    # 主机IP及端口 或随机
    host_port = db.Column(db.String(100), comment='节点指定')
    # 参数，job execute arguments(split by , ex.: arg1=foo,arg2=bar)
    exec_args = db.Column(db.String(1000), comment='运行参数')
    # 优先级 priority
    priority = db.Column(db.Integer, comment='计划优先级')
    # 定时 cron表达式
    cron_exp = db.Column(db.String(100), comment='计划定时')
    is_enabled = db.Column(db.Boolean, default=True, comment='是否开启')  # 0/1

    project = db.relationship("ProjectsModel", back_populates="plans")
    spider = db.relationship("SpidersModel", back_populates="plans")

    def __init__(self, plan_name=None, project_name=None, version_name=None,
                 spider_name=None, **kwargs):
        super().__init__(**kwargs)
        if plan_name:
            self.vc_md5 = get_md5(plan_name)
            self.plan_name = plan_name
        if project_name:
            self.project_md5 = get_md5(project_name)
            self.project_name = project_name
            if version_name and spider_name:
                self.spider_md5 = get_md5(
                    project_name, version_name, spider_name)
        if version_name:
            self.version_name = version_name
        if spider_name:
            self.spider_name = spider_name
        pass

    def to_dict(self):
        return {
            "vc_md5": self.vc_md5,
            "plan_name": self.plan_name,
            "project_name": self.project_name,
            "version_name": self.version_name,
            "spider_name": self.spider_name,
            "host_port": self.host_port,
            "exec_args": self.exec_args,
            "priority": self.priority,
            "cron_exp": self.cron_exp,
            "is_enabled": self.is_enabled,
        }
        pass

    pass


class JobsModel(BaseModel):
    """运行管理"""
    __tablename__ = 'sp_jobs'

    node_md5 = db.Column(
        db.String(100), db.ForeignKey('sp_nodes.vc_md5'), comment="节点MD5")
    project_md5 = db.Column(
        db.String(100), db.ForeignKey('sp_projects.vc_md5'), comment="项目MD5")
    spider_md5 = db.Column(
        db.String(100), db.ForeignKey('sp_spiders.vc_md5'), comment="爬虫MD5")

    # vc_md5 主键，md5(host_port#project_name#job_id)
    plan_name = db.Column(db.String(100), comment='计划名称')
    host_port = db.Column(db.String(100), nullable=False, comment='域名端口')
    project_name = db.Column(db.String(100), nullable=False, comment='项目名称')
    version_name = db.Column(db.String(100), comment='版本名称')
    spider_name = db.Column(db.String(100), comment='爬虫名称')
    job_id = db.Column(db.String(100), nullable=False, comment='作业ID')
    create_time = db.Column(db.DateTime, comment='创建时间')
    start_time = db.Column(db.DateTime, comment='开始时间')
    end_time = db.Column(db.DateTime, comment='结束时间')
    waiting_time = db.Column(db.Integer, comment='等待时间（秒）')
    running_time = db.Column(db.Integer, comment='运行时间（秒）')
    # 运行状态 pending/running/finished/canceled
    job_status = db.Column(db.String(100), comment='作业状态')
    log_status = db.Column(db.Integer, default=-1, comment='日志检索状态')
    log_progress = db.Column(db.Integer, default=0, comment='日志检索进度')

    node = db.relationship("NodesModel", back_populates="jobs")
    project = db.relationship("ProjectsModel", back_populates="jobs")
    spider = db.relationship("SpidersModel", back_populates="jobs")
    exceptions = db.relationship("JobsExceptionsModel", back_populates="job")

    def __init__(self, host_port=None, project_name=None, job_id=None,
                 version_name=None, spider_name=None, **kwargs):
        super().__init__(**kwargs)
        if host_port:
            if project_name and job_id:
                self.vc_md5 = get_md5(host_port, project_name, job_id)
            self.node_md5 = get_md5(host_port)
            self.host_port = host_port
        if project_name:
            self.project_md5 = get_md5(project_name)
            if version_name and spider_name:
                self.spider_md5 = get_md5(
                    project_name, version_name, spider_name)
            self.project_name = project_name
        if version_name:
            self.version_name = version_name
        if spider_name:
            self.spider_name = spider_name
        if job_id:
            self.job_id = job_id
        pass

    def to_dict(self):
        create_time = self.create_time or self.start_time
        waiting_time = time_difference(self.start_time, create_time)
        return {
            "vc_md5": self.vc_md5,
            "plan_name": self.plan_name,
            "host_port": self.host_port,
            "project_name": self.project_name,
            "version_name": self.version_name,
            "spider_name": self.spider_name,
            "job_id": self.job_id,
            "create_time": datetime2str(create_time),
            "start_time": datetime2str(self.start_time),
            "end_time": datetime2str(self.end_time),
            "waiting_time": self.waiting_time or waiting_time,
            "running_time": seconds2time(self.running_time),
            "job_status": self.job_status,
            "log_status": self.log_status,
            "log_progress": self.log_progress,
        }
        pass

    @classmethod
    def get_jobs_retrieving(cls):
        """获取待检索日志的任务"""
        return cls.query.filter(
            cls.job_status != JobStatus.PENDING.value,
            cls.log_status != 1).all()
        pass

    @classmethod
    def get_spiders_statistics_start(cls, hours=12):
        """统计最近启动时间、平均等待时间"""
        today = datetime.datetime.now() - datetime.timedelta(hours=hours)
        foo = db.session.query(
            cls.spider_md5, cls.start_time, cls.waiting_time).filter(
            cls.spider_md5.in_(
                db.session.query(cls.spider_md5).filter(
                    cls.start_time > today).distinct()
            )).subquery()
        return db.session.query(
            foo.c.spider_md5,
            db.func.max(foo.c.start_time).label("start_time_last"),
            db.func.avg(foo.c.waiting_time).label("waiting_time_avg"),
        ).group_by(foo.c.spider_md5).all()
        pass

    @classmethod
    def get_spiders_statistics_end(cls, hours=12):
        """统计平均运行时间、总运行次数"""
        today = datetime.datetime.now() - datetime.timedelta(hours=hours)
        foo = db.session.query(
            cls.spider_md5, cls.running_time).filter(
            db.or_(
                cls.job_status == JobStatus.FINISHED.value,
                cls.job_status == JobStatus.CANCELED.value,
            ),
            cls.spider_md5.in_(
                db.session.query(cls.spider_md5).filter(
                    cls.end_time > today).distinct()
            )).subquery()
        return db.session.query(
            foo.c.spider_md5,
            db.func.avg(foo.c.running_time).label("running_time_avg"),
            db.func.count(foo.c.spider_md5).label("runs_num"),
        ).group_by(foo.c.spider_md5).all()
        pass

    @classmethod
    def get_jobs_no_waiting_time(cls):
        """获取等待时间为空的数据"""
        return cls.query.filter(
            cls.waiting_time.is_(None),
            cls.start_time.isnot(None)).all()
        pass

    pass


class JobsExceptionsModel(BaseModel):
    """运行异常"""
    __tablename__ = 'sp_jobs_exceptions'

    job_md5 = db.Column(
        db.String(100), db.ForeignKey('sp_jobs.vc_md5'), comment="作业MD5")

    # vc_md5 主键，MD5值，md5(host_port#project_name#job_id#exc_time)
    host_port = db.Column(db.String(100), nullable=False, comment='域名端口')
    project_name = db.Column(db.String(100), nullable=False, comment='项目名称')
    version_name = db.Column(db.String(100), comment='版本名称')
    spider_name = db.Column(db.String(100), comment='爬虫名称')
    plan_name = db.Column(db.String(100), comment='计划名称')
    job_id = db.Column(db.String(100), nullable=False, comment='作业ID')
    exc_time = db.Column(db.DateTime, nullable=False, comment='异常时间')
    exc_level = db.Column(db.String(100), comment='异常等级')
    exc_message = db.Column(db.Text, comment='异常信息')
    remark = db.Column(db.Text, comment='备注')
    is_closed = db.Column(db.Boolean, default=False, comment='是否关闭')
    is_emailed = db.Column(
        db.Boolean, default=False, comment='是否邮件；0：未发送；1：已发送')

    job = db.relationship("JobsModel", back_populates="exceptions")

    def __init__(self, host_port=None, project_name=None, job_id=None,
                 exc_time=None, **kwargs):
        super().__init__(**kwargs)
        if exc_time and isinstance(exc_time, str):
            exc_time = datetime.datetime.strptime(exc_time, '%Y-%m-%d %H:%M:%S')
        if host_port and project_name and job_id:
            if exc_time:
                self.vc_md5 = get_md5(
                    host_port, project_name, job_id,
                    exc_time.strftime("%Y-%m-%d %H:%M:%S"))
            self.job_md5 = get_md5(host_port, project_name, job_id)
        if host_port:
            self.host_port = host_port
        if project_name:
            self.project_name = project_name
        if job_id:
            self.job_id = job_id
        if exc_time:
            self.exc_time = exc_time
        pass

    def to_dict(self):
        return {
            "vc_md5": self.vc_md5,
            "job_md5": self.job_md5,
            "host_port": self.host_port,
            "project_name": self.project_name,
            "version_name": self.version_name,
            "spider_name": self.spider_name,
            "plan_name": self.plan_name,
            "job_id": self.job_id,
            "exc_time": datetime2str(self.exc_time),
            "exc_level": self.exc_level,
            "exc_message": self.exc_message,
            "remark": self.remark,
            "is_closed": self.is_closed,
            "is_emailed": self.is_emailed,
        }
        pass

    def get_email_content(self):
        s = ""
        s += "Salve: {}\r\n".format(self.host_port)
        s += "Project: {}\r\n".format(self.project_name)
        s += "Version: {}\r\n".format(self.version_name)
        s += "Spider: {}\r\n".format(self.spider_name)
        s += "Job: {}\r\n".format(self.job_id)
        s += "ExcTime: {}\r\n".format(self.exc_time)
        s += "ExcLevel: {}\r\n".format(self.exc_level)
        s += "ExcMessage: {}\r\n".format(self.exc_message)
        s += "Remark: {}\r\n".format(self.remark)
        return s
        pass

    pass


class SystemSettingsModel(BaseModel):
    """系统设置"""
    __tablename__ = 'sp_settings'

    # vc_md5 主键，MD5值，username计算
    key = db.Column(db.String(100), comment='参数键')
    value = db.Column(db.Text, comment='参数值')

    default_settings = {
        "threshold_cpu": 80,  # CPU使用率 %
        "threshold_virtual_memory": 80,  # 内存使用率 %
        "threshold_swap_memory": 0,  # 交换分区使用率 %
        "threshold_disk_usage": 80,  # 磁盘使用率 %
        "threshold_disk_io_read": 0,  # 磁盘读速率 KB/s
        "threshold_disk_io_write": 0,  # 磁盘写速率 KB/s
        "threshold_net_io_sent": 0,  # 网络发送速率 Kb/s
        "threshold_net_io_receive": 0,  # 网络接收速率 Kb/s
        "default_recipients": "",  # 默认异常报警邮件接收人
        "use_email_alert": False,  # 是否开启邮件报警
    }

    def __init__(self, key=None, **kwargs):
        super().__init__(**kwargs)
        if key:
            self.vc_md5 = get_md5(key)
            self.key = key
        pass

    def to_dict(self):
        return {
            "vc_md5": self.vc_md5,
            "key": self.key,
            "value": self.value,
        }
        pass

    @classmethod
    def init_settings(cls):
        """初始系统配置"""
        exists = {model.key for model in cls.query.filter(cls.vc_md5.in_(
            [get_md5(k) for k in cls.default_settings])).all()}
        for key in set(cls.default_settings.keys()).difference(exists):
            db.session.add(cls(key=key, value=cls.default_settings[key]))
        db.session.commit()
        pass

    @classmethod
    def get_settings(cls):
        """获取系统配置"""
        sys_settings = {}
        for model in cls.query.all():
            key, value = model.key, model.value
            if key.startswith("threshold_"):
                value = int(value)
            elif key.startswith("use_"):
                value = bool(int(value))
            sys_settings[key] = value
        return sys_settings
        pass

    @classmethod
    def set_settings(cls, **kwargs):
        """设置系统设置"""
        for key, value in kwargs.items():
            if key not in cls.default_settings:
                continue
            db.session.merge(cls(key=key, value=value))
        db.session.commit()
        pass

    pass


class RolesModel(BaseModel):
    __tablename__ = 'sp_roles'

    # vc_md5 主键，MD5值，md5(name)
    name = db.Column(db.String(64), unique=True, comment="角色名称")
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)

    users = db.relationship('UsersModel', backref='role', lazy='dynamic')

    def __init__(self, name=None, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        if self.permissions is None:
            self.permissions = 0
        if name is not None:
            self.vc_md5 = get_md5(name)
        pass

    @classmethod
    def insert_roles(cls):
        roles = {
            'Guest': [
                Permission.GUEST,
            ],
            'Standard': [
                Permission.GUEST,
                Permission.STANDARD,
            ],
            'Administrator': [
                Permission.GUEST,
                Permission.STANDARD,
                Permission.ADMINISTRATOR,
            ],
        }
        default_role = 'Guest'
        for r in roles:
            role = cls.query.filter_by(name=r).first()
            if role is None:
                role = cls(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm.value

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm.value

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm.value == perm.value

    def __repr__(self):
        return '<Role %r>' % self.name

    pass


class UsersModel(UserMixin, BaseModel):
    """User继承UserMixin和db.Model类的功能属性"""
    __tablename__ = 'sp_users'

    role_md5 = db.Column(
        db.String(64), db.ForeignKey('sp_roles.vc_md5'), comment="角色ID")

    # vc_md5 主键，MD5值，username计算
    username = db.Column(db.String(64), unique=True, index=True, comment="用户名称")
    password_hash = db.Column(db.String(128), comment="用户密码")
    email = db.Column(db.String(64), index=True, comment="邮箱")
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.datetime.utcnow)
    avatar_hash = db.Column(db.String(32))

    def __init__(self, username=None, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        if self.username is not None:
            self.vc_md5 = get_md5(self.username)
        if self.role is None:
            if self.email == current_app.config['MAIL_ADMIN']:
                self.role = RolesModel.query.filter_by(
                    name='Administrator').first()
            if self.role is None:
                self.role = RolesModel.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()
        self.logger = current_app.logger
        pass

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id}).decode('utf-8')

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except Exception as e:
            self.logger.error(e)
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id}).decode('utf-8')

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except Exception as e:
            self.logger.error(e)
            return False
        user = UsersModel.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps(
            {'change_email': self.id, 'new_email': new_email}).decode('utf-8')

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except Exception as e:
            self.logger.error(e)
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMINISTRATOR)

    def ping(self):
        self.last_seen = datetime.datetime.utcnow()
        db.session.add(self)

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def gravatar(self, size=100, default='identicon', rating='g'):
        url = 'https://secure.gravatar.com/avatar'
        hash_value = self.avatar_hash or self.gravatar_hash()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash_value, size=size, default=default, rating=rating)

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('utf-8')

    def verify_auth_token(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except Exception as e:
            self.logger.error(e)
            return None
        return UsersModel.query.get(data['id'])

    def __repr__(self):
        return '<User %r>' % self.username

    pass


'''========= Enum ========='''


class JobPriority(Enum):
    LOW, NORMAL, HIGH, HIGHEST = range(-1, 3)


class JobRunType(Enum):
    ONETIME = 'onetime'
    PERIODIC = 'periodic'


class JobStatus(Enum):
    """任务状态"""
    # ['pending', 'running', 'finished', 'canceled']
    PENDING = 'pending'
    RUNNING = 'running'
    FINISHED = 'finished'
    CANCELED = 'canceled'
    pass


class Permission(Enum):
    GUEST = 1
    STANDARD = 2
    ADMINISTRATOR = 4
    pass
