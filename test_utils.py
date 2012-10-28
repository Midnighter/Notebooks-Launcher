# -*- coding: utf-8 -*-


"""
======================
Test Utility Functions
======================

:Author:
    Moritz Emanuel Beber
:Date:
    2012-10-26
:Copyright:
    Copyright(c) 2012 Jacobs University of Bremen. All rights reserved.
:File:
    test_utils.py
"""


import os

if os.geteuid() != 0:
    raise StandardError("You need to have superuser privileges to run these tests.")

import pwd
import grp
import nose.tools as nt

from crypt import crypt

if os.uname()[0] == "Linux":
    from linux_utils import *
elif os.uname()[0] == "Darwin":
    from mac_utils import *
else:
    raise StandardError("unkown operating system")


def test_user():
    user1 = {"username": "foo", "sys-pass": "fooman", "secondary": ()}
    user2 = {"username": "bar", "sys-pass": "barman",
            "secondary": ("labtools", "labrats")}
    tests = [user1, user2]
    groups = set()
    for user in tests:
        for group in user["secondary"]:
            groups.add(group)
    groups = tuple(groups)
    for group in groups:
        add_group(group)
        yield check_add_group, group
    for user in tests:
        add_user(user["username"], *user["secondary"])
        yield check_add_user, user["username"], user["secondary"]
        add_password(user["username"], user["sys-pass"])
        yield check_add_password, user["username"], user["sys-pass"]
        for group in groups:
            append_to_group(group, user["username"])
            yield check_append_to_group, group, user["username"]
        delete_user(user["username"])
        yield check_delete_user, user["username"]
    for group in groups:
        delete_group(group)
        yield check_delete_group, group


def check_add_user(username, args):
    reload(pwd)
    reload(grp)
    pw_entry = pwd.getpwnam(username)
    nt.assert_true(os.path.exists(pw_entry.pw_dir))
#    grp_entry = grp.getgrnam(username)
#    nt.assert_equal(pw_entry.pw_uid, grp_entry.gr_gid)
    for group in args:
        secondary = grp.getgrnam(group)
        nt.assert_true(username in secondary.gr_mem)

def check_add_password(username, plain_pw):
    reload(pwd)
    pw_entry = pwd.getpwnam(username)
    crypted_pw = pw_entry.pw_passwd
    run = True
    if pw_entry.pw_passwd in ("x", "*", "********"):
        try:
            from spwd import getspnam
        except ImportError:
            run = False
        else:
            crypted_pw = getspnam(username).sp_pwd
    if run:
        nt.assert_equal(crypt(plain_pw, crypted_pw), crypted_pw)

def check_delete_user(username):
    reload(pwd)
    reload(grp)
    # is there a faster and better (platform independent) check?
    for group in grp.getgrall():
        nt.assert_false(username in group.gr_mem)
    nt.assert_raises(KeyError, pwd.getpwnam, username)
    nt.assert_false(os.path.exists(os.path.expanduser("~{0}".format(username))))

def check_add_group(group):
    reload(grp)
    grp.getgrnam(group)

def check_append_to_group(group, username):
    reload(grp)
    gr_entry = grp.getgrnam(group)
    nt.assert_true(username in gr_entry.gr_mem)

def check_delete_group(group):
    reload(grp)
    nt.assert_raises(KeyError, grp.getgrnam, group)

