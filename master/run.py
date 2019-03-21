#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/8/15
# @Author: lsj
# @File  : run_master.py
# @Desc  :
默认Python版本支持：3.6
gunicorn --worker=3 main:app -b 0.0.0.0:8080
gunicorn -b 127.0.0.1:8000 -k gevent -w 1 app.wsgi

gunicorn --worker=3 run_master:app -b 0.0.0.0:8080
gunicorn -b 127.0.0.1:8000 -k gevent -w 1 run_master
"""
import os
import sys

import click
from dotenv import load_dotenv
from flask_migrate import Migrate, upgrade

from master.agents import register_server
from master.app import create_app
from master.models import UsersModel, RolesModel, Permission
from master.models import NodesModel
from master.models import SystemSettingsModel
from master.models import db
from master.schedulers import start_scheduler

# 使用dotenv管理环境变量 pip install -U python-dotenv
dot_env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dot_env_path):
    load_dotenv(dot_env_path)

# 使用coverage统计python web项目的代码覆盖率
COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage

    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

# Create an application instance that web servers can use.
# We store it as "application" (the wsgi default) and
# also the much shorter and convenient "app".
application = app = create_app(os.getenv('FLASK_CONFIG') or 'production')
print(app.config.items())
register_server()
start_scheduler()
migrate = Migrate(app, db)  # 扩展数据库表结构
RolesModel.insert_roles()
NodesModel.init_master()
SystemSettingsModel.init_settings()


@app.shell_context_processor
def make_shell_context():
    return dict(
        db=db,
        UserModel=UsersModel,
        RoleModel=RolesModel,
        Permission=Permission
    )


@app.cli.command()
@click.option('--coverage/--no-coverage', default=False,
              help='Run tests under code coverage.')
def test(coverage):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import subprocess
        os.environ['FLASK_COVERAGE'] = '1'
        sys.exit(subprocess.call(sys.argv))

    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()


@app.cli.command()
@click.option('--length', default=25,
              help='Number of functions to include in the profiler report.')
@click.option('--profile-dir', default=None,
              help='Directory where profiler data files are saved.')
def profile(length, profile_dir):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()


@app.cli.command()
def deploy():
    """Run deployment tasks."""
    # migrate database to latest revision
    upgrade()

    # create or update user roles
    RolesModel.insert_roles()

    # ensure all users are following themselves
    UsersModel.add_self_follows()
