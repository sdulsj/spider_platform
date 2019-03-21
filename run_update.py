#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通过GIT自动更新程序代码
pip install GitPython
https://gitpython.readthedocs.io/en/stable/intro.html
"""
import os.path
import sys
import os
import functools
from importlib import reload
from git import Repo

# 创建版本库对象
repo = Repo(os.path.dirname(os.path.realpath(__file__)))
assert not repo.bare

print(repo.bare)  # 版本库是否为空版本库
print(repo.is_dirty())  # 当前工作区是否干净
print(repo.untracked_files)  # 版本库中未跟踪的文件列表
print(repo.remotes)  # 获取远程版本库列表
print(repo.branches)  # 查看分支列表
print(repo.active_branch)  # 查看当前分支


# 提交暂存区内容
def git_index_commit(message="this is a test"):
    # Git 术语中，index 表示暂存区，为下次将要提交到版本库里的文件
    index = repo.index  # 索引/暂存区对象 - Index
    index.add(['new.txt'])  # 添加
    index.remove(['old.txt'])  # 移除
    index.commit(message)  # 提交
    pass


# 拉取远程版本库分支至本地
def git_remote_pull(name="origin", refspec="master"):
    remote = repo.remote(name=name)  # 获取默认版本库 origin
    remote.pull(refspec=refspec)  # 从远程版本库拉取分支
    pass


# 推送本地分支至远程版本库
def git_remote_push(name="origin", refspec="master"):
    remote = repo.remote(name=name)  # 获取默认版本库 origin
    remote.push(refspec=refspec)  # 推送本地分支到远程版本库
    pass


# 重命名远程版本库分支
def git_remote_rename(name="origin", new_name="new_origin"):
    remote = repo.remote(name=name)  # 获取默认版本库 origin
    remote.rename(new_name)  # 重命名远程分支
    pass


# 直接执行 Git 命令
def git_commit():
    git = repo.git
    git.add('test1.txt')  # git add test1.txt
    git.commit('-m', 'this is a test')  # git commit -m 'this is a test'
    pass


class Reloader:
    SUFFIX = '.pyc'

    def __init__(self):
        self.mtimes = {}  # time of last modification

    def __call__(self):
        import pdb
        pdb.set_trace()
        for mod in sys.modules.values():
            self.check(mod)

    def check(self, mod):
        if not (mod and hasattr(mod, '__file__') and mod.__file__):
            return
        try:
            mtime = os.stat(mod.__file__).st_mtime
        except (OSError, IOError):
            return
        if mod.__file__.endswith(self.__class__.SUFFIX) and \
                os.path.exists(mod.__file__[:-1]):
            mtime = max(os.stat(mod.__file__[:-1].st_mtime), mtime)
        if mod not in self.mtimes:
            self.mtimes[mod] = mtime
        elif self.mtimes[mod] < mtime:
            try:
                reload(mod)
                self.mtimes[mod] = mtime
            except ImportError:
                pass


reloader = Reloader()
reloader()

if __name__ == '__main__':
    git_remote_pull()  # 拉取
    pass
