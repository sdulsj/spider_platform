#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import re
import traceback
import uuid
from copy import copy

try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

from twisted.python import log
from twisted.web import resource
from slave.utils import UtilsCache
from slave.utils import get_spider_list, native_stringify_dict
from slave.decorators import decorator_auth


class JsonResource(resource.Resource):
    json_encoder = json.JSONEncoder()

    def render(self, request):
        r = resource.Resource.render(self, request)
        return self.render_object(r, request)

    def render_object(self, obj, request):
        r = self.json_encoder.encode(obj) + "\n"
        request.setHeader('Content-Type', 'application/json')
        request.setHeader('Access-Control-Allow-Origin', '*')
        request.setHeader('Access-Control-Allow-Methods',
                          'GET, POST, PATCH, PUT, DELETE')
        request.setHeader('Access-Control-Allow-Headers', ' X-Requested-With')
        request.setHeader('Content-Length', len(r))
        return r


class WsResource(JsonResource):

    def __init__(self, root):
        JsonResource.__init__(self)
        self.root = root

    def render(self, request):
        try:
            return JsonResource.render(self, request).encode('utf-8')
        except Exception as e:
            if self.root.debug:
                return traceback.format_exc().encode('utf-8')
            log.err()
            r = {
                "node_name": self.root.node_name,
                "status": "error",
                "message": str(e)
            }
            return self.render_object(r, request).encode('utf-8')


class DaemonStatus(WsResource):
    """
    daemon_status.json
    To check the load status of a service.

    Supported Request Methods: GET
    Parameters: none

    Example request:
    curl -u test:test http://localhost:6800/daemon_status.json
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok",
        "pending": "0",
        "running": "0",
        "finished": "0"
    }

    """

    @decorator_auth
    def render_GET(self, request):
        pending = sum(q.count() for q in self.root.poller.queues.values())
        running = len(self.root.launcher.processes)
        finished = len(self.root.launcher.finished)

        return {
            "node_name": self.root.node_name,
            "status": "ok",
            "pending": pending,
            "running": running,
            "finished": finished
        }


class Schedule(WsResource):
    """
    schedule.json
    Schedule a spider run (also known as a job), returning the job id.

    Supported Request Methods: POST
    Parameters:
    project (string, required) - the project name
    spider (string, required) - the spider name
    setting (string, optional) - a Scrapy setting to use when running the spider
    job (string, optional) - a job id used to identify the job, overrides the
                               default generated UUID
    _version (string, optional) - the version of the project to use
    any other parameter is passed as spider argument

    Example request:
    $ curl -u test:test http://localhost:6800/schedule.json -d project=myProject -d spider=example
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok",
        "job": "6487ec79947edab326d6db28a2d86511e8247444"
    }

    """

    @decorator_auth
    def render_POST(self, request):
        args = native_stringify_dict(copy(request.args), keys_only=False)
        settings = args.pop('setting', [])
        settings = dict(x.split('=', 1) for x in settings)
        args = dict((k, v[0]) for k, v in args.items())
        project = args.pop('project')
        spider = args.pop('spider')
        version = args.get('_version', '')
        spiders = get_spider_list(project, version=version)
        if spider not in spiders:
            return {
                "status": "error",
                "message": "spider '%s' not found" % spider
            }
        args['settings'] = settings
        job_id = args.pop('job', uuid.uuid1().hex)
        args['_job'] = job_id
        self.root.scheduler.schedule(project, spider, **args)
        return {
            "node_name": self.root.node_name,
            "status": "ok",
            "job": job_id
        }


class Cancel(WsResource):
    """
    cancel.json
    Cancel a spider run (aka. job).
    If the job is pending, it will be removed.
    If the job is running, it will be terminated.

    Supported Request Methods: POST
    Parameters:
    project (string, required) - the project name
    job (string, required) - the job id

    Example request:
    $ curl -u test:test http://localhost:6800/cancel.json -d project=myProject -d job=6487ec79947edab326d6db28a2d86511e8247444
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok",
        "prev_state": "running"
    }

    """

    @decorator_auth
    def render_POST(self, request):
        args = native_stringify_dict(copy(request.args), keys_only=False)
        args = dict((k, v[0]) for k, v in args.items())
        project = args['project']
        job_id = args['job']
        signal = args.get('signal', 'TERM')
        prev_state = None
        queue = self.root.poller.queues[project]
        c = queue.remove(lambda x: x["_job"] == job_id)
        if c:
            prev_state = "pending"
        spiders = self.root.launcher.processes.values()
        for s in spiders:
            if s.job == job_id:
                s.transport.signalProcess(signal)
                prev_state = "running"
        return {
            "node_name": self.root.node_name,
            "status": "ok",
            "prev_state": prev_state
        }


class AddVersion(WsResource):
    """
    add_version.json
    Add a version to a project, creating the project if it doesn't exist.

    Supported Request Methods: POST
    Parameters:
    project (string, required) - the project name
    version (string, required) - the project version
    egg (file, required) - a Python egg containing the project’s code

    Example request:
    $ curl -u test:test http://localhost:6800/add_version.json -F project=myProject -F version=r23 -F egg=@output.egg
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok",
        "projects": "myProject",
        "versions": "r99",
        "spiders": 3
    }

    """

    @decorator_auth
    def render_POST(self, request):
        project = request.args[b'project'][0].decode('utf-8')
        version = request.args[b'version'][0].decode('utf-8')
        egg_file = BytesIO(request.args[b'egg'][0])
        self.root.egg_storage.put(egg_file, project, version)
        spiders = get_spider_list(project, version=version)
        self.root.update_projects()
        UtilsCache.invalid_cache(project)
        return {
            "node_name": self.root.node_name,
            "status": "ok",
            "project": project,
            "version": version,
            "spiders": len(spiders)
        }


class ListProjects(WsResource):
    """
    list_projects.json
    Get the list of projects uploaded to this Scrapy server.

    Supported Request Methods: GET
    Parameters: none

    Example request:
    $ curl -u test:test http://localhost:6800/list_projects.json
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok",
        "projects": ["myProject", "otherProject"]
    }

    """

    @decorator_auth
    def render_GET(self, request):
        projects = list(self.root.scheduler.list_projects())
        return {
            "node_name": self.root.node_name,
            "status": "ok",
            "projects": projects
        }


class ListVersions(WsResource):
    """
    list_versions.json
    Get the list of versions available for some project.
    The versions are returned in order,
    the last one is the currently used version.

    Supported Request Methods: GET
    Parameters:
    project (string, required) - the project name

    Example request:
    $ curl -u test:test http://localhost:6800/list_versions.json?project=myProject
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok",
        "versions": ["r99", "r156"]
    }

    """

    @decorator_auth
    def render_GET(self, request):
        args = native_stringify_dict(copy(request.args), keys_only=False)
        project = args['project'][0]
        versions = self.root.egg_storage.list(project)
        return {
            "node_name": self.root.node_name,
            "status": "ok",
            "versions": versions
        }


class ListSpiders(WsResource):
    """
    list_spiders.json
    Get the list of spiders available in the last (unless overridden) version
    of some project.

    Supported Request Methods: GET
    Parameters:
    project (string, required) - the project name
    _version (string, optional) - the version of the project to examine

    Example request:
    $ curl -u test:test http://localhost:6800/list_spiders.json?project=myProject
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok",
        "spiders": ["spider1", "spider2", "spider3"]
    }

    """

    @decorator_auth
    def render_GET(self, request):
        args = native_stringify_dict(copy(request.args), keys_only=False)
        project = args['project'][0]
        version = args.get('_version', [''])[0]
        spiders = get_spider_list(
            project, runner=self.root.runner, version=version)
        return {
            "node_name": self.root.node_name,
            "status": "ok",
            "spiders": spiders
        }


class ListJobs(WsResource):
    """
    list_jobs.json
    Get the list of pending, running and finished jobs of some project.

    Supported Request Methods: GET
    Parameters:
    project (string, required) - the project name

    Example request:
    $ curl -u test:test http://localhost:6800/list_jobs.json?project=myProject
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok",
        "pending": [
            {
                "id": "78391cc0fcaf11e1b0090800272a6d06",
                "spider": "spider1"
            }
        ],
        "running": [
            {
                "id": "422e608f9f28cef127b3d5ef93fe9399",
                "spider": "spider2",
                "start_time": "2012-09-12 10:14:03.594664"
            }
        ],
        "finished": [
            {
                "id": "2f16646cfcaf11e1b0090800272a6d06",
                "spider": "spider3",
                "start_time": "2012-09-12 10:14:03.594664",
                "end_time": "2012-09-12 10:24:03.594664"
            }
        ]
    }
    """

    @decorator_auth
    def render_GET(self, request):
        args = native_stringify_dict(copy(request.args), keys_only=False)
        project = args['project'][0]
        spiders = self.root.launcher.processes.values()
        running = [
            {
                "id": s.job,
                "spider": s.spider,
                "pid": s.pid,
                "start_time": s.start_time.isoformat(' ')
            } for s in spiders if s.project == project
        ]
        queue = self.root.poller.queues[project]
        pending = [
            {
                "id": x["_job"],
                "spider": x["name"]
            } for x in queue.list()
        ]
        finished = [
            {
                "id": s.job,
                "spider": s.spider,
                "start_time": s.start_time.isoformat(' '),
                "end_time": s.end_time.isoformat(' ')
            } for s in self.root.launcher.finished if s.project == project
        ]
        return {
            "node_name": self.root.node_name,
            "status": "ok",
            "pending": pending,
            "running": running,
            "finished": finished
        }


class DeleteProject(WsResource):
    """
    del_version.json
    Delete a project version.
    If there are no more versions available for a given project,
    that project will be deleted too.

    Supported Request Methods: POST
    Parameters:
    project (string, required) - the project name
    version (string, required) - the project version

    Example request:
    $ curl -u test:test http://localhost:6800/del_version.json -d project=myProject -d version=r99
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok"
    }

    """

    @decorator_auth
    def render_POST(self, request):
        args = native_stringify_dict(copy(request.args), keys_only=False)
        project = args['project'][0]
        self._delete_version(project)
        UtilsCache.invalid_cache(project)
        return {
            "node_name": self.root.node_name,
            "status": "ok"
        }

    def _delete_version(self, project, version=None):
        self.root.egg_storage.delete(project, version)
        self.root.update_projects()


class DeleteVersion(DeleteProject):
    """
    del_project.json
    Delete a project and all its uploaded versions.

    Supported Request Methods: POST
    Parameters:
    project (string, required) - the project name

    Example request:
    $ curl -u test:test http://localhost:6800/del_project.json -d project=myProject
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok"
    }

    """

    @decorator_auth
    def render_POST(self, request):
        args = native_stringify_dict(copy(request.args), keys_only=False)
        project = args['project'][0]
        version = args['version'][0]
        self._delete_version(project, version)
        UtilsCache.invalid_cache(project)
        return {
            "node_name": self.root.node_name,
            "status": "ok"
        }


class JobException(WsResource):
    """
    job_exception.json
    Get spider job exception by reading the log file.

    Supported Request Methods: POST
    Parameters:
    project (string, required) - the project name
    spider (string, required) - the spider name
    job (string, required) - the job id
    offset (string, optional) - seek offset position, default 0

    Example request:
    $ curl -u test:test http://localhost:6800/job_exception.json -d project=myProject -d spider=example -d job=8d47b9e2d80311e8b8ba7c67a203577c
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok",
        "whence": 3000,
        "errors": []
    }

    """
    # log level：CRITICAL > ERROR > WARNING > INFO > DEBUG,NOTSET
    delimiter = '&' * 10  # Log block delimiter
    comp_block = re.compile(
        pattern=r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[.*?\] ' +
                r'(CRITICAL|ERROR|WARNING|INFO|DEBUG|NOTSET):)',
        flags=re.I)  # log sub RegEx
    comp_error = re.compile(
        pattern=r'((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[.*?\] ' +
                r'(CRITICAL|ERROR):[\s\S]+?)([\r\n]+{}|\s*$)'.format(delimiter),
        flags=re.I)  # log search RegEx

    @decorator_auth
    def render_POST(self, request):
        try:
            args = native_stringify_dict(copy(request.args), keys_only=False)
            args = dict((k, v[0]) for k, v in args.items())
            project = args['project']  # project name
            spider = args['spider']  # spider name
            job_id = args['job']  # job id
            offset = int(args.get('offset', 0))  # seek offset position
            logs_dir = self.root.logs_dir  # logs directory
            log_path = os.path.join(
                logs_dir, project, spider, "{}.log".format(job_id))
            with open(log_path, "r", encoding='UTF-8') as f:
                f.seek(offset)  # f.seek(0, 2)
                lines = f.read()  # Go to the end of file
                whence = f.tell()  # curr position
                f.close()
            errors = self.comp_error.findall(
                string=self.comp_block.sub(
                    repl=r'{}\1'.format(self.delimiter), string=lines))
            errors = [(e[1], e[2], e[0]) for e in errors]
            return {
                "node_name": self.root.node_name,
                "status": "ok",
                "whence": whence,
                "errors": errors
            }
        except Exception as e:
            return {
                "node_name": self.root.node_name,
                "status": "error",
                "message": str(e)
            }


class SysPerformance(WsResource):
    """
    sys_performance.json
    Get system performance indicators, such as CPU

    Supported Request Methods: GET
    Parameters: none

    Example request:
    curl -u test:test http://localhost:6800/sys_performance.json
    Example response:
    {
        "node_name": "nodeName",
        "status": "ok",
        "performance":
            {
                "cpu": 5.9,
                "virtual_memory": 83.4,
                "swap_memory": 81.8,
                "disk_usage": 42.5,
                "disk_io_read": 0.0,
                "disk_io_write": 0.0,
                "net_io_sent": 0.05,
                "net_io_receive": 0.07
            }
    }

    """

    @decorator_auth
    def render_GET(self, request):
        per = self.root.performance
        return {
            "node_name": self.root.node_name,
            "status": "ok",
            "performance": {
                'cpu': per.cpu_percent,
                'virtual_memory': per.virtual_memory_percent,
                'swap_memory': per.swap_memory_percent,
                'disk_usage': per.disk_usage_percent,
                'disk_io_read': per.disk_io_read_speed,
                'disk_io_write': per.disk_io_write_speed,
                'net_io_sent': per.net_io_sent_speed,
                'net_io_receive': per.net_io_receive_speed,
            }
        }
