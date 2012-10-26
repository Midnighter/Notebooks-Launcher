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
import random
import time


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
        # find a unique uid still a limited and potentially slow approach
        new_uid = random.randint(501, 3000)
        while subprocess.call(["id", str(new_uid)]) == 0:
            new_uid = random.randint(501, 3000)
        # set new unique user ID
        execute_command(["dscl", ".", "-create", user, "UniqueID", str(new_uid)])
        # set user's group ID property
        execute_command(["dscl", ".", "-create", user, "PrimaryGroupID",
                str(new_uid)])
        # set home directory
        execute_command(["dscl", ".", "-create", user, "NFSHomeDirectory",
            "/Local{0}".format(user)])
        # still need to create $HOME?
        execute_command(["createhomedir", "-c"])
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
        # create the new group
        execute_command(["dscl", ".", "-create", group])
        # find a unique gid; still a limited and potentially slow approach
        new_gid = random.randint(501, 3000)
        while subprocess.call(["id", str(new_gid)]) == 0:
            new_gid = random.randint(501, 3000)
        # set new unique gid
        execute_command(["dscl", ".", "-append", group, "gid", str(new_gid)])
        # is setting a password necessary?
#        execute_command(["dscl", ".", "-append", group, "passwd", "*"])
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

def pgrep(username, process):
    pids = list()
    try:
        plist = execute_command(["ps", "-u", username, "-xo", "pid,command,args"])
    except subprocess.CalledProcessError as err:
        LOGGER.warn(err.output.strip())
        return pids
    for line in plist.split("\n"):
        if process in line:
            pids.append(int(line.split()[0]))
    return pids

def kill_process(username, process):
    # must not fail, i.e., user must exist on the system
    for pid in pgrep(username, process):
        try:
            execute_command(["kill", str(pid)])
        except subprocess.CalledProcessError as err:
            LOGGER.warn(err.output.strip())
    time.sleep(0.1)
    # force quit remaining matches
#    nasties = pgrep(username, process)
#    if not nasties:
#        return
#    for pid in nasties:
#        try:
#            execute_command(["kill", "-9", str(pid)])
#        except subprocess.CalledProcessError as err:
#            LOGGER.warn(err.output.strip())
#    time.sleep(0.1)
    # verify that indeed all processes have been terminated
    if pgrep(username, process):
        LOGGER.warn(u"User '{0}' still has running notebook kernel(s).".format(
                username))

def delete_user(usr):
    rc = 0
    try:
        # remove user from all secondary groups
        groups = execute_command(["id", "-nG", usr["username"]])
        for grp in groups.split():
            execute_command(["dscl", ".", "-delete",
                    "/Groups/{0}".format(grp), "GroupMembership", usr["username"]])
        # delete the passwd entry
        execute_command(["dscl", ".", "-delete",
                "/Users/{0}".format(usr["username"]), "Password"])
        # delete the primary group
        execute_command(["dscl", ".", "-delete",
                "/Groups/{0}".format(usr["username"])])
        # delete the user
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

