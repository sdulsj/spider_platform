#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import socket
from datetime import datetime

from scrapy.utils.misc import load_object
from six.moves.urllib.parse import urlparse
from twisted.application.service import IServiceCollection
from twisted.web import resource, static

from .interfaces import IPoller, IEggStorage, ISpiderScheduler, IPerformance


class Root(resource.Resource):

    def __init__(self, config, app):
        resource.Resource.__init__(self)
        self.debug = config.getboolean('debug', False)
        self.runner = config.get('runner')
        self.logs_dir = config.get('logs_dir')  # logs directory
        items_dir = config.get('items_dir')
        local_items = items_dir and (
                urlparse(items_dir).scheme.lower() in ['', 'file'])
        self.app = app
        self.node_name = config.get('node_name', socket.gethostname())
        self.putChild(b'', Home(self, local_items))
        if self.logs_dir:
            self.putChild(
                b'logs',
                static.File(
                    self.logs_dir.encode('ascii', 'ignore'), 'text/plain')
            )
        if local_items:
            self.putChild(b'items', static.File(items_dir, 'text/plain'))
        self.putChild(b'jobs', Jobs(self, local_items))
        services = config.items('services', ())
        for svc_name, svc_cls_name in services:
            svc_cls = load_object(svc_cls_name)
            self.putChild(svc_name.encode('utf-8'), svc_cls(self))
        self.update_projects()
        # Authorization
        usr, pwd = config.get("username", ""), config.get("password", "")
        if usr or pwd:
            bytes_auth = "{}:{}".format(usr, pwd).encode("utf-8")
            self.auth = b"Basic " + base64.encodebytes(bytes_auth).strip()
        else:
            self.auth = None
        pass

    def update_projects(self):
        self.poller.update_projects()
        self.scheduler.update_projects()

    @property
    def launcher(self):
        app = IServiceCollection(self.app, self.app)
        return app.getServiceNamed('launcher')

    @property
    def scheduler(self):
        return self.app.getComponent(ISpiderScheduler)

    @property
    def egg_storage(self):
        return self.app.getComponent(IEggStorage)

    @property
    def poller(self):
        return self.app.getComponent(IPoller)

    @property
    def performance(self):
        return self.app.getComponent(IPerformance)


class Home(resource.Resource):

    def __init__(self, root, local_items):
        resource.Resource.__init__(self)
        self.root = root
        self.local_items = local_items

    def render_GET(self, request):
        data = {
            'projects': ', '.join(self.root.scheduler.list_projects())
        }
        s = """
<html>
<head><title>Spider Platform Slave</title></head>
<body>
<h1>Spider Platform Slave</h1>
<p>Expand based on Scrapyd v1.2</p>
<p>Available projects: <b>%(projects)s</b></p>
<ul>
<li><a href="/jobs">Jobs</a></li>
""" % data
        if self.local_items:
            s += '<li><a href="/items/">Items</a></li>'
        s += """
<li><a href="/logs/">Logs</a></li>
<li><a href="http://scrapyd.readthedocs.org/en/latest/">Documentation</a></li>
</ul>

<h2>How to schedule a spider?</h2>

<p>To schedule a spider you need to use the API (this web UI is only for
monitoring)</p>

<p>Example using <a href="http://curl.haxx.se/">curl</a>:</p>
<p><code>curl http://localhost:6800/schedule.json -d project=default -d spider=somespider</code></p>

<p>For more information about the API, see the <a href="http://scrapyd.readthedocs.org/en/latest/">Scrapyd documentation</a></p>
</body>
</html>
"""
        return s.encode('utf-8')


class Jobs(resource.Resource):

    def __init__(self, root, local_items):
        resource.Resource.__init__(self)
        self.root = root
        self.local_items = local_items

    def render(self, request):
        cols = 8
        tr = "<tr><th colspan='%s' style='background-color: #ddd'>%s</th></tr>"

        s = "<html><head><title>Spider Platform Slave</title></head>"
        s += "<body><h1>Jobs</h1><p><a href='..'>Go back</a></p>"
        s += "<table border='1'><tr>"
        s += "<th>Project</th><th>Spider</th><th>Job</th><th>PID</th>"
        s += "<th>Start</th><th>Runtime</th><th>Finish</th><th>Log</th>"
        if self.local_items:
            s += "<th>Items</th>"
            cols = 9
        s += "</tr>"
        s += tr % (cols, "Pending")
        for project, queue in self.root.poller.queues.items():
            for m in queue.list():
                s += "<tr>"
                s += "<td>%s</td>" % project
                s += "<td>%s</td>" % str(m['name'])
                s += "<td>%s</td>" % str(m['_job'])
                s += "</tr>"
        s += tr % (cols, "Running")
        for p in self.root.launcher.processes.values():
            s += "<tr>"
            for a in ['project', 'spider', 'job', 'pid']:
                s += "<td>%s</td>" % getattr(p, a)
            s += "<td>%s</td>" % p.start_time.replace(microsecond=0)
            s += "<td>%s</td>" % (datetime.now().replace(
                microsecond=0) - p.start_time.replace(microsecond=0))
            s += "<td></td>"
            s += "<td><a href='/logs/%s/%s/%s.log'>Log</a></td>" % (
                p.project, p.spider, p.job)
            if self.local_items:
                s += "<td><a href='/items/%s/%s/%s.jl'>Items</a></td>" % (
                    p.project, p.spider, p.job)
            s += "</tr>"
        s += tr % (cols, "Finished")
        for p in self.root.launcher.finished:
            s += "<tr>"
            for a in ['project', 'spider', 'job']:
                s += "<td>%s</td>" % getattr(p, a)
            s += "<td></td>"
            s += "<td>%s</td>" % p.start_time.replace(microsecond=0)
            s += "<td>%s</td>" % (p.end_time.replace(
                microsecond=0) - p.start_time.replace(microsecond=0))
            s += "<td>%s</td>" % p.end_time.replace(microsecond=0)
            s += "<td><a href='/logs/%s/%s/%s.log'>Log</a></td>" % (
                p.project, p.spider, p.job)
            if self.local_items:
                s += "<td><a href='/items/%s/%s/%s.jl'>Items</a></td>" % (
                    p.project, p.spider, p.job)
            s += "</tr>"
        s += "</table>"
        s += "</body>"
        s += "</html>"

        request.setHeader('Content-Type', 'text/html; charset=utf-8')
        request.setHeader('Content-Length', len(s))

        return s.encode('utf-8')
