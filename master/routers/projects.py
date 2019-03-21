#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/8/15
# @Author: lsj
# @File  : views.py
# @Desc  : 
默认Python版本支持：3.6
"""
from distutils.dist import DistributionMetadata

from flask import Blueprint
from flask import flash, jsonify, redirect, render_template, request
from flask import url_for
from flask_login import login_required

from master.agents import agent
from master.extensions import send_emails
from master.models import JobsExceptionsModel
from master.models import ProjectsModel
from master.models import SystemSettingsModel

blueprint_project = Blueprint('project', __name__)


@blueprint_project.route("/manage")
@login_required
def project_manage():
    return render_template("projects/manage.html")
    pass


@blueprint_project.route("/search", methods=['post'])
@login_required
def project_search():
    page_index = request.form.get('pageNum', 1)
    page_size = request.form.get('pageSize', 10)
    keywords = request.form.get('keywords')
    pagination = ProjectsModel.get_pagination(
        page_index=page_index, page_size=page_size, keywords=keywords)
    return jsonify(pagination)
    pass


@blueprint_project.route("/select", methods=['post'])
@login_required
def project_select():
    file = request.files.get('file')
    if not file:
        return
    import tempfile

    with tempfile.TemporaryFile() as f:
        file.save(f)
        metadata = DistributionMetadata()
        metadata.read_pkg_file(f)
        data = {
            'project_name': metadata.name,
            'version_name': metadata.version,
        }
        return jsonify(data)
    pass


@blueprint_project.route("/deploy", methods=['post'])
@login_required
def project_deploy():
    """
    deploy 发布相关操作
    :return:
    """
    file = request.files.get('file')
    if not file:
        flash('No selected file')
        return redirect(request.referrer)
    project_name = request.form.get('project_name')
    version_name = request.form.get('version_name')
    agent.deploy_project(file, project_name, version_name)
    flash('deploy success!')
    return redirect(request.referrer)
    pass


@blueprint_project.route("/delete/<project_name>")
@blueprint_project.route("/delete/<project_name>/<version_name>")
@login_required
def project_delete(project_name, version_name=None):
    """
    delete 删除相关操作
    :return:
    """
    agent.delete_project(project_name=project_name, version_name=version_name)
    flash('delete success!')
    return redirect(request.referrer)
    pass


"""========= detail ========="""


@blueprint_project.route("/detail/<vc_md5>")
@login_required
def project_detail_manage(vc_md5):
    model = ProjectsModel.get_first(vc_md5=vc_md5)
    if not model:
        return redirect(url_for('project.project_manage'))
    project_name = model.project_name
    project_id = model.vc_md5
    return render_template(
        "projects/detail.html",
        project_name=project_name, project_id=project_id)


@blueprint_project.route("/detail/search", methods=['post'])
@login_required
def project_detail_search():
    keywords = request.form.get('keywords')
    data_id = request.form.get('dataID')
    model = ProjectsModel.get_first(vc_md5=data_id, keywords=keywords)
    return jsonify(model.get_versions() if model else {})


@blueprint_project.route("/exception/send")
@login_required
def project_exception_send():
    sys_conf = SystemSettingsModel.get_settings()
    if not sys_conf.get("use_email_alert"):
        print('End email exception job, the email alert is closed')
        return
    default_recipients = sys_conf.get("default_recipients")
    for project in ProjectsModel.get_list():
        recipients = project.recipients or default_recipients
        if not recipients:
            continue
        recipients = recipients.split(";")
        subject = "Project({}) Exception".format(project.project_name)
        template = "projects/email/exceptions"
        exceptions = [m.to_dict() for m in JobsExceptionsModel.get_limit(
            is_closed=False, is_emailed=False, project_md5=project.vc_md5)]
        send_emails(subject, template, *recipients, exceptions=exceptions)
        pass


'''========= other ========='''


@blueprint_project.route("/start/<project_name>/<spider_name>/<version_name>")
@login_required
def project_spider_start(project_name, spider_name, version_name=None):
    job_id = agent.start_spider(
        project_name=project_name, spider_name=spider_name,
        version_name=version_name)
    flash('Start success! {}'.format(job_id))
    return redirect(request.referrer)
