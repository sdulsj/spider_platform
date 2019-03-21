#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask

from master import __version__
from master.config import config
from master.extensions import bootstrap
from master.extensions import login_manager
from master.extensions import mail
from master.models import db


def create_app(config_name):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    # app.app_context().push()

    with app.app_context():  # 添加这一句，否则会报找不到application和context错误
        bootstrap.init_app(app)
        mail.app = app
        mail.init_app(app)
        # moment.init_app(app)
        db.app = app
        db.init_app(app)  # 初始化db
        db.create_all(app=app)  # 创建所有未创建的table
        login_manager.init_app(app)
        # page_down.init_app(app)
        if app.config['SSL_REDIRECT']:
            from flask_sslify import SSLify
            ssl_ify = SSLify(app)

    # Register blueprint(s)
    from master.routers.views import blueprint_main
    from master.routers.nodes import blueprint_node
    from master.routers.projects import blueprint_project
    from master.routers.plans import blueprint_plan
    from master.routers.systems import blueprint_system
    from master.routers.auth import blueprint_auth
    from master.routers.jobs import blueprint_job
    app.register_blueprint(blueprint_main)
    app.register_blueprint(blueprint_node, url_prefix='/node')
    app.register_blueprint(blueprint_project, url_prefix='/project')
    app.register_blueprint(blueprint_plan, url_prefix='/plan')
    app.register_blueprint(blueprint_job, url_prefix='/job')
    app.register_blueprint(blueprint_system, url_prefix='/system')
    app.register_blueprint(blueprint_auth, url_prefix='/auth')

    @app.context_processor
    def inject():
        return dict(title="SpiderPlatform", version=__version__)

    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            db.session.rollback()
        db.session.remove()

    @app.teardown_appcontext
    def teardown_request(exception=None):
        if exception:
            db.session.rollback()
        db.session.remove()

    print(app.url_map)
    return app
