#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/8/15
# @Author: lsj
# @File  : views.py
# @Desc  : 
默认Python版本支持：3.6
"""
from flask import flash, jsonify, redirect, render_template, request
from flask_login import login_required

from master.models import NodesModel, NodesExceptionsModel
from master.models import SystemSettingsModel
from master.agents import agent
from flask import Blueprint

blueprint_system = Blueprint('system', __name__)


# 节点异常列表
@blueprint_system.route("/settings")
@login_required
def system_settings():
    settings = SystemSettingsModel.get_settings()
    print(settings)
    return render_template("systems/settings.html", **settings)
    pass


@blueprint_system.route("/update", methods=['post'])
@login_required
def system_settings_update():
    kwargs = request.form.to_dict()
    kwargs["use_email_alert"] = True if kwargs.get("use_email_alert") else False
    SystemSettingsModel.set_settings(**kwargs)
    flash('Update success!')
    return redirect(request.referrer)
    pass


'''========= detail&exception ========='''


# 异常列表
@blueprint_system.route("/detail/manage")
@login_required
def system_detail_manage():
    model = NodesModel.get_first(node_type="master")
    node_id = model.vc_md5 if model else None
    return render_template("systems/exceptions.html", node_id=node_id)


@blueprint_system.route("/detail/status", methods=['post'])
@login_required
def system_detail_status():
    return jsonify(agent.get_master_performance())
    pass


@blueprint_system.route("/exception/search", methods=['post'])
@login_required
def system_exception_search():
    page_index = request.form.get('pageNum', 1)
    page_size = request.form.get('pageSize', 10)
    node_md5 = request.form.get('dataID')
    is_closed = request.form.get('dataType', False)
    keywords = request.form.get('keywords')
    # 查询分页结果集
    pagination = NodesExceptionsModel.get_pagination(
        page_index=page_index, page_size=page_size,
        is_closed=is_closed, node_md5=node_md5,
        keywords=keywords)
    return jsonify(pagination)


# 备注信息保存
@blueprint_system.route("/exception/update", methods=['post'])
@login_required
def system_exception_update():
    vc_md5 = request.form.get('id', request.form.get('vc_md5'))
    act = request.form.get('act')
    # 更新
    kwargs = request.form.to_dict()
    # 处理checkBox值
    is_closed = True if 'is_closed' in kwargs else False
    NodesExceptionsModel.update_one(
        vc_md5=vc_md5, is_closed=is_closed, remark=kwargs.get('remark', ''))
    flash('{} success!'.format(act))
    return redirect('/client/exception/manage', code=302)
    pass


# 备注信息保存
@blueprint_system.route("/exception/delete/<exception_md5>")
@login_required
def system_exception_delete(exception_md5):
    NodesExceptionsModel.del_one(vc_md5=exception_md5)
    flash('Delete success!')
    return redirect(request.referrer)
    pass
