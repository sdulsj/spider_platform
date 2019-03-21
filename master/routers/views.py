#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/8/15
# @Author: lsj
# @File  : views.py
# @Desc  : 
默认Python版本支持：3.6
"""
import datetime
import os
import traceback

from flask import Blueprint
from flask import abort, current_app, flash, redirect, send_from_directory
from flask import render_template, request, jsonify
from flask_login import login_required
from flask_sqlalchemy import get_debug_queries
from werkzeug.exceptions import HTTPException

from master.agents import agent
from master.models import Permission, UsersModel, NodesExceptionsModel

blueprint_main = Blueprint('main', __name__)


@blueprint_main.route("/")
@blueprint_main.route("/dashboard")
@login_required
def index():
    return render_template('dashboard.html')
    pass


@blueprint_main.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(blueprint_main.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon')
    pass


@blueprint_main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'


@blueprint_main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission, UserModel=UsersModel)


@blueprint_main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response


# @app.before_request
def intercept_no_project():
    if request.path.find('/project//') > -1:
        flash("create project first")
        return redirect("/project/manage", code=302)


# @app.context_processor
def inject_common():
    return dict(now=datetime.datetime.now(), servers=agent.servers)


"""========= error ========="""


@blueprint_main.errorhandler(401)
def unauthorized(e):
    return render_template('errors/401.html'), 401


@blueprint_main.app_errorhandler(403)
def forbidden(e):
    if (request.accept_mimetypes.accept_json
            and not request.accept_mimetypes.accept_html):
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return render_template('errors/403.html'), 403


@blueprint_main.app_errorhandler(404)
def page_not_found(e):
    if (request.accept_mimetypes.accept_json
            and not request.accept_mimetypes.accept_html):
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return render_template('errors/404.html'), 404


@blueprint_main.app_errorhandler(500)
def internal_server_error(e):
    if (request.accept_mimetypes.accept_json
            and not request.accept_mimetypes.accept_html):
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    return render_template('errors/500.html'), 500


@blueprint_main.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    # app.logger.error(traceback.print_exc())
    msg = '{}==>{}\r\n{}'.format(type(e), e, traceback.print_exc())
    current_app.logger.error(msg)  # 写入日志
    # NodesExceptionsModel.merge_exception(msg)  # 写入数据库
    NodesExceptionsModel.merge_one(
        host_port="Master",
        node_type="master",
        exc_time=datetime.datetime.now(),
        exc_level="ERROR",
        exc_message=msg
    )
    return jsonify({
        'code': code,
        'success': False,
        'msg': str(e),
        'data': None
    })
