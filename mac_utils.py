# -*- coding: utf-8 -*-


"""
=========================
Utility Functions for Mac
=========================

:Author:
    Moritz Emanuel Beber
:Date:
    2012-10-25
:Copyright:
    Copyright(c) 2012 Jacobs University of Bremen. All rights reserved.
:File:
    mac_utils.py
"""


__all__ = ["add_user", "add_group", "add_password", "append_to_group",
        "kill_process", "delete_user", "delete_group"]

import logging
import subprocess


LOGGER = logging.getLogger()


def add_user(username, *args):
    rc = 0
    user = "/Users/{0}".format(username)
    try:
        # create new user entry
        execute_command(["dscl", ".", "-create", user])
        # set shell
        execute_command(["dscl", ".", "-create", user, "UserShell", "/bin/bash"])
        # set full name
#        execute_command(["dscl", ".", "-create", "/Users/%s" % user["username"],
#                "RealName", "%s %s" % (user["name"], user["surname"])])
        # find existing user IDs (limited to 256)
        output = execute_command(["dscl", ".", "-list", "/Users", "uid"])
        uids = [int(line.split()[1]) for line in output.split("\n") if line]
        new_uid = max(uids) + 1
        # set new unique user ID
        execute_command(["dscl", ".", "-create", user, "UniqueID", str(new_uid)])
        # set user's group ID property TODO: must be unique?
        execute_command(["dscl", ".", "-create", user, "PrimaryGroupID", "80"])
        # create and set home directory
        execute_command(["dscl", ".", "-create", user, "NFSHomeDirectory",
            "/Local{0}".format(user)])
        # add user to secondary group(s)
        for group in args:
            execute_command(["dscl", ".", "-append", "/Groups/{0}".format(group),
                    "GroupMembership", username])
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        rc = err.returncode
    return rc

def add_group(groupname):
    rc = 0
    group = "/Groups/{0}".format(groupname)
    try:
        execute_command(["dscl", ".", "-create", group])
        output = execute_command(["dscl", ".", "-list", "/Groups", "gid"])
        gids = [int(line.split()[1]) for line in output.split("\n") if line]
        new_gid = max(gids) + 1
        execute_command(["dscl", ".", "-append", group, "gid", str(new_gid)])
        execute_command(["dscl", ".", "-append", group, "passwd", "*"])
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        rc = err.returncode
    return rc

def add_password(username, new_pw):
    rc = 0
    try:
        execute_command(["dscl", ".", "-passwd", "/Users/{0}".format(username),
            new_pw])
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        rc = err.returncode
    return rc

def append_to_group(groupname, username):
    rc = 0
    try:
        execute_command(["dscl", ".", "-append", "/Groups/{0}".format(groupname),
                    "GroupMembership", username])
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
    # verify that indeed all processes have been terminated
    try:
        assert 1 == subprocess.call(["pgrep", "-u", username, "-f", process])
    except AssertionError:
        LOGGER.warn(u"User '{0}' still has running notebook kernel(s).".format(
                username))

def delete_user(usr):
    rc = 0
    try:
        execute_command(["dscl", ".", "-delete",
                "/Groups/{0}".format(usr["username"])])
        execute_command(["dscl", ".", "-delete",
                "/Users/{0}".format(usr["username"])])
        usr["sys-pass"] = ""
        usr["nb-pass"] = ""
        LOGGER.info(u"Removed user '{0}'.".format(usr["username"]))
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        rc = err.returncode
    return rc

def delete_group(groupname):
    rc = 0
    try:
        execute_command(["dscl", ".", "-delete",
                "/Groups/{0}".format(groupname)])
        LOGGER.info(u"Removed group '{0}'.".format(groupname))
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        rc = err.returncode
    return rc

from notebooks import execute_command

