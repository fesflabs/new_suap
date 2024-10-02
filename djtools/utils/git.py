# -*- coding: utf-8 -*-
import os
import subprocess
from django.conf import settings


__all__ = ['diff', 'diff2', 'modified_files', 'modified_apps', ]


def diff(branch):
    cmd = 'git merge-base origin/master {}'.format(branch)
    previous_commit = subprocess.run(cmd.split(' '), capture_output=True).stdout.decode('utf-8').strip()
    cmd = 'git diff {} --name-only'.format(previous_commit)
    return subprocess.run(cmd.split(' '), capture_output=True).stdout.decode('utf-8').strip()


def diff2(branch):
    cmd = 'git diff origin/master origin/{} --name-only'.format(branch)
    result = subprocess.run(cmd.split(' '), capture_output=True)
    stdout = result.stdout.decode('utf-8')
    return stdout


def modified_files(branch, pattern=None, exists_only=False):
    diff_content = diff(branch).strip()
    files = diff_content.split('\n') if diff_content else []
    if pattern:
        files = [f for f in files if pattern in f]
    if exists_only:
        files = [f for f in files if os.path.exists(f)]
    return files


def modified_apps(branch, pattern=None, exists_only=False):
    apps = []
    tokens = set()
    for file_path in modified_files(branch, pattern=pattern, exists_only=exists_only):
        tokens.add(file_path.split('/')[0])
    for token in tokens:
        if token in settings.INSTALLED_APPS:
            apps.append(token)
    return apps
