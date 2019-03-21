import os

from master.settings import MAIL_KWARGS

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # 在未设置SERVER_NAME的情况下，url_for生成的绝对URL是依赖于请求的URL的
    # 若要生成不依赖于request的绝对URL（比如异步发送邮件时在邮件中生成网站某个页面的URL），就必须要设置SERVER_NAME
    # 一般SERVER_NAME设置为网站的域名
    # SERVER_NAME = "127.0.0.1:5000"
    # THREADS_PER_PAGE = 2
    # CSRF_ENABLED = True
    # CSRF_SESSION_KEY = "secret"
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SSL_REDIRECT = False

    # Flask-Mail 配置
    MAIL_SERVER = MAIL_KWARGS.get("host")  # 电子邮件服务器的主机名或IP地址
    MAIL_PORT = MAIL_KWARGS.get("port")  # 电子邮件服务器的端口
    MAIL_USE_TLS = MAIL_KWARGS.get("use_tls")  # 启用传输层安全协议
    MAIL_USE_SSL = MAIL_KWARGS.get("use_ssl")  # 启用安全套接层协议
    MAIL_USERNAME = MAIL_KWARGS.get("username")  # 邮件账户用户名
    MAIL_PASSWORD = MAIL_KWARGS.get("password")  # 邮件账户的密码
    MAIL_SUBJECT_PREFIX = '[SpiderPlatform]'
    MAIL_ADMIN = MAIL_KWARGS.get("sender")
    MAIL_SENDER = 'SpiderPlatform Admin <{}>'.format(MAIL_ADMIN)
    MAIL_RECIPIENTS = MAIL_KWARGS.get("recipients")

    # Flask-SQLAlchemy配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_ECHO = False
    ITEMS_PER_PAGE = 20
    SLOW_DB_QUERY_TIME = 0.5

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    SERVER_NAME = "127.0.0.1:5000"
    DEBUG = True

    _DB_URI = 'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or _DB_URI


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False

    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite://'

    pass


class ProductionConfig(Config):
    _DB_URI = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _DB_URI

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # email errors to the administrators
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.MAIL_SENDER,
            toaddrs=[cls.MAIL_ADMIN],
            subject=cls.MAIL_SUBJECT_PREFIX + ' Application Error',
            credentials=credentials,
            secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


class HerokuConfig(ProductionConfig):
    SSL_REDIRECT = True if os.environ.get('DYNO') else False

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # handle reverse proxy server headers
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class DockerConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class UnixConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # log to syslog
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.INFO)
        app.logger.addHandler(syslog_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'heroku': HerokuConfig,
    'docker': DockerConfig,
    'unix': UnixConfig,

    'default': DevelopmentConfig
}
