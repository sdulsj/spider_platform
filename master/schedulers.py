#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/1/24
# @Author: lsj
# @File  : schedulers.py
# @Desc  : 调度Scheduler
"""

import datetime
import os
import time

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler

import master.settings as settings
from master.agents import agent
from master.models import JobsModel, JobsExceptionsModel
from master.models import NodesModel, NodesExceptionsModel
from master.models import PlansModel
from master.models import ProjectsModel, SpidersModel
from master.models import SystemSettingsModel
from master.utils import get_logger, time_difference, EmailOperationHelper

# 定义调度 Define apscheduler
scheduler = BackgroundScheduler()
logger = get_logger('Scheduler',
                    os.path.join(settings.DIR_LOGS, 'scheduler.log'),
                    settings.LOG_LEVEL)

'''========= Scheduler ========='''


# 通过调度同步节点状态
def sync_sys_performance_job():
    logger.info('Start sync sys performance job')
    agent.poll_system_performance()
    logger.info('End sync sys performance job')
    pass


# 通过调度同步节点状态
def sync_slaves_status_job():
    logger.info('Start sync slaves status job')
    agent.sync_slaves_status()
    logger.info('End sync slaves status job')
    pass


# 通过调度同步节点异常
def sync_nodes_exception_job():
    logger.info('Start sync nodes exception job')
    agent.sync_nodes_exception()
    logger.info('End sync nodes exception job')
    pass


# 通过调度同步项目列表
def sync_projects_list_job():
    """
    sync projects
    通过调度同步项目列表
    :return:
    """
    logger.info('Start sync projects list job')
    agent.sync_projects_list()
    logger.info('End sync projects list job')
    pass


# 通过调度同步爬虫列表
def sync_spiders_list_job():
    """
    sync spiders
    通过调度同步爬虫列表
    :return:
    """
    logger.info('Start sync spiders list job')
    agent.sync_spiders_list()
    logger.info('End sync spiders list job')
    pass


# 通过调度同步爬虫运行状态
def sync_jobs_status_job():
    """
    sync job execution running status
    通过调度同步爬虫运行状态
    :return:
    """
    logger.info('Start sync jobs status job')
    agent.sync_jobs_status()
    logger.info('End sync jobs status job')
    pass


def sync_jobs_exception_job():
    logger.info('Start sync jobs exception job')
    agent.sync_jobs_exception()
    logger.info('End sync jobs exception job')
    pass


# 通过调度发送异常邮件
def sync_email_exception_job():
    """
    email exception by scheduler
    通过调度发送异常邮件
    :param self:
    :return:
    """
    logger.info('Start email exception job')
    eoh = EmailOperationHelper(**settings.MAIL_KWARGS)
    sys_conf = SystemSettingsModel.get_settings()
    if not sys_conf.get("use_email_alert"):
        logger.info('End email exception job, the email alert is closed')
        return
    default_recipients = sys_conf.get("default_recipients")
    for node in NodesModel.get_list():
        recipients = node.recipients or default_recipients
        if not recipients:
            continue
        recipients = recipients.split(";")
        subject = "Node({}-{}) Exception of SpiderPlatform".format(
            node.node_type, node.host_port)
        models = NodesExceptionsModel.get_limit(
            is_closed=False, is_emailed=False, node_md5=node.vc_md5)
        if not models:
            continue
        content = "\r\n\r\n".join([m.get_email_content() for m in models])
        eoh.send_mail(subject, content, recipients=recipients)
        for model in models:
            NodesExceptionsModel.update_one(model=model, is_emailed=True)
        pass
    for project in ProjectsModel.get_list():
        recipients = project.recipients or default_recipients
        if not recipients:
            continue
        recipients = recipients.split(";")
        subject = "Project({}) Exception of SpiderPlatform".format(
            project.project_name)
        models = JobsExceptionsModel.get_limit(
            is_closed=False, is_emailed=False,
            project_name=project.project_name)
        if not models:
            continue
        content = "\r\n\r\n".join([m.get_email_content() for m in models])
        eoh.send_mail(subject, content, recipients=recipients)
        for model in models:
            JobsExceptionsModel.update_one(model=model, is_emailed=True)
        pass
    logger.info('End email exception job')
    pass


def sync_spider_statistics_job():
    # 处理等待时间空值
    for model in JobsModel.get_jobs_no_waiting_time():
        create_time = model.create_time or model.start_time
        JobsModel.update_one(
            model=model,
            create_time=create_time,
            waiting_time=time_difference(create_time, model.start_time)
        )
    # 统计最近启动时间、平均等待时间
    statistics = JobsModel.get_spiders_statistics_start()
    for spider_md5, start_time_last, waiting_time_avg in statistics:
        SpidersModel.update_one(
            vc_md5=spider_md5,
            start_time_last=start_time_last,
            waiting_time_avg=waiting_time_avg,
        )
    # 统计平均运行时间、总运行次数
    statistics = JobsModel.get_spiders_statistics_end()
    for spider_md5, running_time_avg, runs_num in statistics:
        SpidersModel.update_one(
            vc_md5=spider_md5,
            running_time_avg=running_time_avg,
            runs_num=runs_num
        )
    pass


# 添加定时任务至调度队列
def reload_runnable_spider_job_execution():
    """
    添加定时任务至调度队列
    add periodic job to scheduler
    :return:
    """

    # 通过调度运行爬虫任务
    def run_spider_job(project_name, spider_name, **spider_settings):
        """
        run spider by scheduler
        通过调度运行爬虫任务
        :param project_name: 项目名称
        :param spider_name: 爬虫名称
        :return:
        """
        msg = "{}-{}".format(project_name, spider_name)
        logger.info('Start run spider job:{}'.format(msg))
        agent.start_spider(project_name, spider_name, **spider_settings)
        logger.info('End run spider job:{}'.format(msg))
        pass

    logger.info('Start reload runnable spider job execution')
    running_job_ids = set([job.id for job in scheduler.get_jobs()])
    # app.logger.debug('[running_job_ids] %s' % ','.join(running_job_ids))
    available_job_ids = set()
    # add new job to schedule
    keys = ["second", "minute", "hour", "day", "month", "day_of_week", "year"]
    for plan in PlansModel.get_list(is_enabled=True):
        job_id = "spider_job_{}_{}".format(
            plan.vc_md5, int(time.mktime(plan.dt_update.timetuple())))
        available_job_ids.add(job_id)
        if job_id in running_job_ids:
            continue
        try:
            args = plan.project_name, plan.spider_name
            kwargs = {
                "version_name": plan.version_name,
                "exec_args": plan.exec_args,
                "priority": plan.priority,
                "host_port": plan.host_port,
                "plan_name": plan.plan_name,
            }
            trigger_args = dict(zip(keys, plan.cron_exp.strip().split()))
            scheduler.add_job(
                run_spider_job, args=args, kwargs=kwargs,
                trigger='cron', id=job_id,
                max_instances=999, misfire_grace_time=60 * 60,
                coalesce=True, **trigger_args)
        except Exception as e:
            logger.error(
                '[load_spider_job] failed {} {}, '
                'may be cron expression format error '.format(job_id, str(e)))
        logger.info(
            '[load_spider_job][project:%s][spider:%s][plan:%s][job_id:%s]' % (
                plan.project_name, plan.spider_name, plan.plan_name, job_id))
    # remove invalid jobs
    for invalid_job_id in filter(lambda x: x.startswith("spider_job_"),
                                 running_job_ids.difference(available_job_ids)):
        scheduler.remove_job(invalid_job_id)
        logger.info('[drop_spider_job][job_id:%s]' % invalid_job_id)
    logger.info('End reload runnable spider job execution')
    pass


def my_listener(event):
    """
    监听Scheduler发出的事件并作出处理，如任务执行完、任务出错等
    :param event: Scheduler 事件
    :return:
    """
    if event.exception:
        # or logger.fatal
        logger.critical('The job of {} crashed :('.format(event.job_id))
        msg = '{}==>{}\r\n{}'.format(type(event.exception), event.exception,
                                     event.traceback)
        logger.error(msg)  # 写入日志
        # NodesExceptionsModel.merge_exception(msg)  # 写入数据库
        NodesExceptionsModel.merge_one(
            host_port="Master",
            node_type="master",
            exc_time=datetime.datetime.now(),
            exc_level="ERROR",
            exc_message=msg
        )
    else:
        logger.info('The job of {} worked :)'.format(event.job_id))


scheduler.add_listener(my_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
# max_instances=10,
scheduler.add_job(sync_sys_performance_job, 'interval',
                  seconds=5, id="sync_sys_performance_job")
scheduler.add_job(sync_slaves_status_job, 'interval',
                  seconds=30, id="sync_slaves_status_job")
scheduler.add_job(sync_nodes_exception_job, 'interval',
                  seconds=60, id="sync_nodes_exception_job")
scheduler.add_job(sync_projects_list_job, 'interval',
                  seconds=20, id="sync_projects_list_job")
scheduler.add_job(sync_jobs_status_job, 'interval',
                  seconds=20, id="sync_jobs_status_job")
scheduler.add_job(sync_jobs_exception_job, 'interval',
                  seconds=20, id="sync_jobs_exception_job")
scheduler.add_job(sync_spider_statistics_job, 'interval',
                  seconds=20, id="sync_spider_statistics_job")
scheduler.add_job(reload_runnable_spider_job_execution, 'interval',
                  seconds=30, id="reload_runnable_spider_job_execution")
scheduler.add_job(sync_email_exception_job, 'interval',
                  seconds=60, id='sync_email_exception_job')


# start sync job status scheduler
def start_scheduler():
    scheduler.start()
