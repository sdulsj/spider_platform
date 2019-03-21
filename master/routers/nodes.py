#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/8/15
# @Author: lsj
# @File  : views.py
# @Desc  : 
默认Python版本支持：3.6
"""
import re

from flask import Blueprint
from flask import flash, jsonify, redirect, render_template, request, session
from flask_login import login_required

from master.agents import agent
from master.extensions import send_emails
from master.models import NodesModel, NodesExceptionsModel
from master.models import SystemSettingsModel

blueprint_node = Blueprint('node', __name__)


@blueprint_node.route("/manage")
@login_required
def node_manage():
    return render_template('nodes/manage.html')
    pass


@blueprint_node.route("/search", methods=['post'])
@login_required
def node_search():
    page_index = request.form.get('pageNum', 1)
    page_size = request.form.get('pageSize', 10)
    keywords = request.form.get('keywords')
    pagination = NodesModel.get_pagination(
        page_index=page_index, page_size=page_size, keywords=keywords,
        node_type="slave")
    return jsonify(pagination)
    pass


@blueprint_node.route("/merge", methods=['post'])
@login_required
def node_merge():
    """新增/更新（编辑）相关操作"""
    act = request.form.get('act')
    # 新增或更新
    model = NodesModel.merge_one(**request.form.to_dict())
    if model:
        agent.merge_client(model.host_port, model.username, model.password)
    flash('{} success!'.format(act))
    return redirect(request.referrer)
    pass


@blueprint_node.route("/delete/<node_md5>")
@login_required
def node_delete(node_md5):
    """删除相关操作"""
    model = NodesModel.del_one(vc_md5=node_md5)
    if model:
        agent.delete_client(model.host_port)
    flash('delete success!')
    return redirect(request.referrer)
    pass


'''========= detail&exception ========='''


# 节点异常列表
@blueprint_node.route("/detail/<node_md5>")
@login_required
def node_detail_manage(node_md5):
    model = NodesModel.get_first(vc_md5=node_md5)
    if model:
        node_type = model.node_type
        group_name = model.group_name
        host_port = model.host_port
        node_id = model.vc_md5
    else:
        node_type = group_name = host_port = node_id = ""

    return render_template(
        "nodes/detail.html",
        node_type=node_type, group_name=group_name,
        host_port=host_port, node_id=node_id)


@blueprint_node.route("/detail/status", methods=['post'])
@login_required
def node_detail_status():
    vc_md5 = request.form.get('id', request.form.get('vc_md5'))
    if vc_md5:
        model = NodesModel.get_first(vc_md5=vc_md5)
        if model:
            return jsonify(agent.get_salve_performance(model.host_port))
    return jsonify({})
    pass


@blueprint_node.route("/exception")
@login_required
def node_exception_manage():
    return render_template("nodes/exceptions.html")


@blueprint_node.route("/exception/search", methods=['post'])
@login_required
def node_exception_search():
    page_index = request.form.get('pageNum', 1)
    page_size = request.form.get('pageSize', 10)
    node_md5 = request.form.get('dataID')
    is_closed = request.form.get('dataType', False)
    keywords = request.form.get('keywords')
    # 查询分页结果集
    if node_md5:
        pagination = NodesExceptionsModel.get_pagination(
            page_index=page_index, page_size=page_size,
            is_closed=is_closed, node_md5=node_md5, keywords=keywords)
    else:
        pagination = NodesExceptionsModel.get_pagination(
            page_index=page_index, page_size=page_size,
            is_closed=is_closed, node_type="slave", keywords=keywords)
    return jsonify(pagination)


# 备注信息保存
@blueprint_node.route("/exception/update", methods=['post'])
@login_required
def node_exception_update():
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
@blueprint_node.route("/exception/delete/<exception_md5>")
@login_required
def node_exception_delete(exception_md5):
    NodesExceptionsModel.del_one(vc_md5=exception_md5)
    flash('Delete success!')
    return redirect(request.referrer)
    pass


# 备注信息保存
@blueprint_node.route("/exception/send")
@login_required
def node_exception_send():
    sys_conf = SystemSettingsModel.get_settings()
    if not sys_conf.get("use_email_alert"):
        print('End email exception job, the email alert is closed')
        return
    default_recipients = sys_conf.get("default_recipients")
    for node in NodesModel.get_list():
        recipients = node.recipients or default_recipients
        if not recipients:
            continue
        recipients = recipients.split(";")
        subject = "Node({}-{}) Exception".format(
            node.node_type, node.host_port)
        template = "nodes/email/exceptions"
        exceptions = [m.to_dict() for m in NodesExceptionsModel.get_limit(
            is_closed=False, is_emailed=False, node_md5=node.vc_md5)]
        send_emails(subject, template, *recipients, exceptions=exceptions)
        pass
    pass


'''========= other ========='''


# @blueprint_client.route("/status")
# @login_required
def client_status():
    return render_template('nodes/client_status.html')
    pass


# @blueprint_client.route("/index", methods=['post'])
# @login_required
def client_index():
    delta = request.form.get('delta')
    # %Y-%m-%d %H:%M:%S
    keys = {
        "W": "weeks",
        "D": "days",
        "H": "hours",
        "M": "minutes",
        "S": "seconds"
    }
    kwargs = dict()
    for v, k in re.findall(pattern=r'(\d+)([A-Z])', string=delta):
        if k in keys:
            kwargs[keys[k]] = int(v)
        pass
    indexes = agent.stats_index(**kwargs)
    return jsonify(indexes)
    pass


# @blueprint_client.route("/session")
# @blueprint_client.route("/session/<client_md5>")
# @login_required
def client_session(client_md5=None):
    if client_md5:
        model = NodesModel.get_first(vc_md5=client_md5)
        if model:
            session['client_md5'] = model.vc_md5
            session['host_port'] = model.host_port
            return redirect(request.referrer)
    session['client_md5'] = None
    session['host_port'] = None
    return redirect(request.referrer)
    pass
