# -*- coding: utf-8 -*-


"""
===========================
Utility Functions for Linux
===========================

:Author:
    Moritz Emanuel Beber
:Date:
    2012-10-25
:Copyright:
    Copyright(c) 2012 Jacobs University of Bremen. All rights reserved.
:File:
    linuxutils.py
"""


__all__ = ["add_user", "add_group", "add_password", "append_to_group",
        "kill_process", "delete_user", "delete_group"]


import logging
import subprocess
import time
import pexpect

from genericutils import execute_command


LOGGER = logging.getLogger()


def add_user(username, secondary=[]):
    rc = 0
    try:
        if secondary:
            execute_command(["useradd", "-m", "-G", ",".join(secondary), username])
        else:
            execute_command(["useradd", "-m", username])
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        rc = err.returncode
    return rc

def add_group(groupname):
    rc = 0
    try:
        execute_command(["groupadd", "-f", groupname])
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        rc = err.returncode
    return rc

def add_password(username, new_pw):
# the --stdin parameter to passwd is not stable, and if the user already exists
# this fails anyway, so the pexpect version is better
#        ps = subprocess.Popen(["passwd", "--stdin", user["username"]],
#                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
#                stderr=subprocess.PIPE)
#        (stdout, stderr) = ps.communicate(user["password"])
#        if stderr:
#            raise OSError(ps.returncode, stderr)
#        elif ps.returncode != 0:
#            raise OSError(ps.returncode, stdout)
    # TODO: error catching
    rc = 0
    try:
        password = pexpect.spawn(u"passwd {0}".format(username))
        for repeat in (1, 2):
            password.expect(u"password: ")
            password.sendline(new_pw)
            time.sleep(0.1)
    except Exception as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(str(err))
        rc = 1
    return rc

def append_to_group(groupname, username):
    rc = 0
    try:
        execute_command(["usermod", "-aG", groupname, username])
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        rc = err.returncode
    return rc

def kill_process(username, process):
    # must not fail, i.e., user must exist on the system
    try:
        execute_command(["pkill", "-u", username, "-f", process])
    except subprocess.CalledProcessError as err:
        LOGGER.warn(err.output.strip())
    time.sleep(0.2)
    # verify that indeed all processes have been terminated
    if 0 == subprocess.call(["pgrep", "-u", username, "-f", process]):
        LOGGER.warn(u"User '{0}' still has running notebook kernel(s).".format(
                username))

def delete_user(username):
    rc = 0
    try:
        # remove the user from all secondary groups
        execute_command(["usermod", "-G", username, username])
        # delete the passwd entry
        execute_command(["passwd", "-d", username])
        # delete the user account
        execute_command(["userdel", "-r", username])
        LOGGER.info(u"Removed user '%s'.", username)
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        rc = err.returncode
    return rc

def delete_group(groupname):
    rc = 0
    try:
        execute_command(["groupdel", groupname])
        LOGGER.info(u"Removed group '{0}'.".format(groupname))
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        rc = err.returncode
    return rc

