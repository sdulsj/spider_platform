#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/8/15
# @Author: lsj
# @File  : views.py
# @Desc  : 
默认Python版本支持：3.6
"""

from flask import Blueprint
from flask import flash, jsonify, redirect, render_template, request
from flask_login import login_required

from master.agents import agent
from master.models import PlansModel

blueprint_plan = Blueprint('plan', __name__)


@blueprint_plan.route("/manage")
@login_required
def plan_manage():
    return render_template("plans/manage.html")


@blueprint_plan.route("/search", methods=['post'])
@login_required
def plan_search():
    page_index = request.form.get('pageNum', 1)
    page_size = request.form.get('pageSize', 10)
    keywords = request.form.get('keywords')
    pagination = PlansModel.get_pagination(
        page_index=page_index, page_size=page_size, keywords=keywords)
    return jsonify(pagination)
    pass


@blueprint_plan.route("/merge", methods=['post'])
@login_required
def plan_merge():
    """新增/更新（编辑）相关操作"""
    act = request.form.get('act')
    # 新增或更新
    kwargs = request.form.to_dict()
    # 处理checkBox值
    kwargs['is_enabled'] = True if 'is_enabled' in kwargs else False
    PlansModel.merge_one(**kwargs)
    flash('{} success!'.format(act))
    return redirect('/plan/manage', code=302)
    pass


@blueprint_plan.route("/delete/<plan_md5>")
@login_required
def plan_delete(plan_md5):
    """删除相关操作"""
    PlansModel.del_one(vc_md5=plan_md5)
    flash('Delete success!')
    return redirect(request.referrer)
    pass


@blueprint_plan.route("/projects", methods=['post'])
@login_required
def get_projects():
    result = list(agent.projects.keys())
    return jsonify(result)


@blueprint_plan.route("/versions", methods=['post'])
@login_required
def get_versions():
    project_name = request.form.get("projectName")
    result = agent.egg_storage.list(project_name)
    return jsonify(result)


@blueprint_plan.route("/spiders", methods=['post'])
@login_required
def get_spiders():
    project_name = request.form.get("projectName")
    version_name = request.form.get("versionName")
    result = list(agent.projects.get(project_name, {}).get(version_name, set()))
    return jsonify(result)


@blueprint_plan.route("/clients", methods=['post'])
@login_required
def get_clients():
    result = list(agent.slaves.keys())
    return jsonify(result)
