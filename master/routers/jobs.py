#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/8/15
# @Author: lsj
# @File  : views.py
# @Desc  : 
默认Python版本支持：3.6
"""
import requests
from flask import Blueprint
from flask import jsonify, redirect, render_template, request, flash
from flask_login import login_required

from master.agents import agent
from master.models import JobsModel, JobsExceptionsModel

blueprint_job = Blueprint('job', __name__)


@blueprint_job.route("/manage")
@login_required
def job_manage():
    return render_template("jobs/manage.html")


@blueprint_job.route("/search", methods=['post'])
@login_required
def job_search():
    page_index = request.form.get('pageNum', 1)
    page_size = request.form.get('pageSize', 10)
    job_status = request.form.get('dataType', 'running')
    keywords = request.form.get('keywords')
    pagination = JobsModel.get_pagination(
        page_index=page_index, page_size=page_size,
        job_status=job_status, keywords=keywords)
    return jsonify(pagination)
    pass


@blueprint_job.route("/log/<execution_id>")
@login_required
def job_log(execution_id):
    job = JobsModel.get_first(vc_md5=execution_id)
    url = agent.log_url(
        job.host_port, job.project_name, job.spider_name, job.job_id)
    res = requests.get(url)
    res.encoding = 'utf8'
    raw = res.text
    return render_template("jobs/log.html", log_lines=raw.split('\n'))


@blueprint_job.route("/stop/<execution_id>")
@login_required
def job_stop(execution_id):
    job = JobsModel.get_first(vc_md5=execution_id)
    if job:
        if agent.cancel_spider(job.host_port, job.project_name, job.job_id):
            flash('Cancel success!')
    return redirect(request.referrer, code=302)


@blueprint_job.route("/delete/<execution_id>")
@login_required
def job_delete(execution_id):
    model = JobsModel.del_one(vc_md5=execution_id)
    if model:
        flash('Delete success!')
    return redirect(request.referrer, code=302)


'''========= exception ========='''


# 异常列表
@blueprint_job.route("/exception/manage")
@login_required
def job_exception_manage():
    return render_template("jobs/exceptions.html")


# 异常查询
@blueprint_job.route("/exception/search", methods=['post'])
@login_required
def job_exception_search():
    page_index = request.form.get('pageNum', 1)
    page_size = request.form.get('pageSize', 10)
    # is_closed = bool(int(request.form.get('dataType', False)))
    is_closed = request.form.get('dataType', False)
    keywords = request.form.get('keywords')
    # 查询分页结果集
    pagination = JobsExceptionsModel.get_pagination(
        page_index=page_index, page_size=page_size,
        is_closed=is_closed, keywords=keywords)
    return jsonify(pagination)


# 异常操作
@blueprint_job.route("/exception/update", methods=['post'])
@login_required
def job_exception_update():
    vc_md5 = request.form.get('id', request.form.get('vc_md5'))
    kwargs = request.form.to_dict()
    # 处理checkBox值
    is_closed = True if 'is_closed' in kwargs else False
    JobsExceptionsModel.update_one(
        vc_md5=vc_md5, is_closed=is_closed, remark=kwargs.get('remark', ''))
    flash('Update success!')
    return redirect('/job/exception/manage', code=302)
    pass


@blueprint_job.route("/exception/delete/<exception_md5>")
@login_required
def job_exception_delete(exception_md5):
    JobsExceptionsModel.del_one(vc_md5=exception_md5)
    flash('Delete success!')
    return redirect(request.referrer)
    pass
