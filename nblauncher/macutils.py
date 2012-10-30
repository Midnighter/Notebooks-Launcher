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
    macutils.py
"""


__all__ = ["add_user", "add_group", "add_password", "append_to_group",
        "kill_process", "delete_user", "delete_group"]

import logging
import subprocess
import grp
import pwd

from .genericutils import execute_command


LOGGER = logging.getLogger()


class GetUID(object):
    """
    """

    uid = 501

    def __init__(self, **kw_args):
        super(GetUID, self).__init__(**kw_args)
        max_uid = max(pw_entry.pw_uid for pw_entry in pwd.getpwall())
        self.__class__.uid = max(self.__class__.uid, max_uid)

    def __call__(self):
        self.__class__.uid += 1
        return self.__class__.uid


class GetGID(object):
    """
    """

    gid = 501

    def __init__(self, **kw_args):
        super(GetGID, self).__init__(**kw_args)
        max_gid = max(gr_entry.gr_gid for gr_entry in grp.getgrall())
        self.__class__.gid = max(self.__class__.gid, max_gid)

    def __call__(self):
        self.__class__.gid += 1
        return self.__class__.gid


def add_user(username, secondary=[]):
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
        new_uid = GetUID()
        # set new unique user ID
        execute_command(["dscl", ".", "-create", user, "UniqueID", str(new_uid())])
        # set user's primary group ID property to be 'staff'
        staff = grp.getgrnam("staff")
        execute_command(["dscl", ".", "-create", user, "PrimaryGroupID",
                str(staff.gr_gid)])
        # set home directory
        execute_command(["dscl", ".", "-create", user, "NFSHomeDirectory", user])
        # still need to create $HOME?
        execute_command(["createhomedir", "-c"])
        # add user to secondary group(s)
        for group in secondary:
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
        new_gid = GetGID()
        # set new unique gid
        execute_command(["dscl", ".", "-append", group, "gid", str(new_gid())])
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

def delete_user(username):
    rc = 0
    user = "/Users/{0}".format(username)
    try:
        # remove user from all secondary groups
        groups = [group for group in grp.getgrall() if username in group.gr_mem]
#        groups = execute_command(["dscl", ".", "-search", "/Groups", username])
        # id also returns system groups: unsuitable
#        groups = execute_command(["id", "-nG", usr["username"]])
#        groups = set(groups.split())
#        groups.remove("staff")
        for group in groups:
#            if grp.getgrnam(group).gr_gid < 500:
#                continue
            try:
                execute_command(["dscl", ".", "-delete",
                    "/Groups/{0}".format(group.gr_name), "GroupMembership",
                    username])
            except subprocess.CalledProcessError:
                LOGGER.debug(u"pssst:", exc_info=True)
        # delete the passwd entry
        uuid = execute_command(["dscl", ".", "-read", user, "GeneratedUID"])
        uuid = uuid.split(":")[1].strip()
        execute_command(["rm", "-f",
                "/private/var/db/shadow/hash/{0}".format(uuid)])
        # delete the primary group
#        execute_command(["dscl", ".", "-delete",
#                "/Groups/{0}".format(usr["username"])])
        # delete the user
        execute_command(["dscl", ".", "-delete", user])
        # delete home dir
        execute_command(["rm", "-rf", user])
        LOGGER.info(u"Removed user '{0}'.".format(username))
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

