#!/usr/bin/env python
# -*- coding: utf-8 -*-
from threading import Thread

from flask import current_app, render_template
from flask_bootstrap import Bootstrap
from flask_celery import Celery
from flask_login import LoginManager, AnonymousUserMixin
from flask_mail import Mail, Message
from flask_moment import Moment

from master.models import UsersModel

bootstrap = Bootstrap()

moment = Moment()
celery = Celery()


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

    pass


login_manager = LoginManager()
# login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    """
    加载用户的回调函数接收以Unicode字符串形式表示的用户标示符
    如果能找到用户，这个函数必须返回用户对象，否则返回None。
    :param user_id: 用户ID/用户标识
    :return:
    """
    return UsersModel.query.get(user_id)  # int(user_id)


mail = Mail()


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr


def send_emails(subject, template, *to, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['MAIL_SENDER'], recipients=list(to))
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
