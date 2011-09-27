#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
======================================
Configure IPython Notebook Environment
======================================

:Author:
    Moritz Emanuel Beber
:Date:
    2011-09-01
:Copyright:
    Copyright(c) 2011 Jacobs University of Bremen. All rights reserved.
:File:
    setup_notebooks.py
"""


import sys
import os
import shutil
import pwd
import grp
import subprocess
import errno
import string
import random
import csv
import ConfigParser
import time
import pexpect


def tree_copy(src, dst):
    """
    Iteratively copies a folder structure to a destination rooted somewhere
    else.

    Ignores symlinks and mount points.
    """
    if not os.path.exists(dst):
        os.makedirs(dst)
    for name in os.listdir(src):
        src_path = os.path.join(src, name)
        if os.path.isfile(src_path):
            # copy file to destination
            shutil.copy2(src_path, dst)
        elif os.path.isdir(src_path):
            # continue down the directory
            tree_copy(src_path, os.path.join(dst, name))
        # ignoring links and mount points


def create_user_environment(user, config):
    """
    Sets up the user working directories needed.

    Creates a user account if necessary, creates a password for it, adds it to
    a general usergroup, copies specified material into the user directory, and
    makes the user the owner of those files and directories.
    """
    # check for existance of user
    name = user["email"].split("@")[0]
    name = name.split(".")
    username = "".join(name)
    try:
        pw_entry = pwd.getpwnam(username)
    except KeyError:
        # add a new user
        ps = subprocess.Popen(["useradd", "-m", "-G", config["group"], username],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = ps.communicate()
        if stderr:
            raise OSError(ps.returncode, stderr)
        elif ps.returncode != 0:
            raise OSError(ps.returncode, stdout)
        # set the (weak) password using numbers, letters, and the exclamation
        # mark
        user["password"] = "".join(random.choice(config["passwd_selection"])\
                for x in range(config["passwd_length"]))
# the --stdin parameter to passwd is not stable, and if the user already exists
# this fails anyway, so the pexpect version is better
#        ps = subprocess.Popen(["passwd", "--stdin", username],
#                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
#                stderr=subprocess.PIPE)
#        (stdout, stderr) = ps.communicate(user["password"])
#        if stderr:
#            raise OSError(ps.returncode, stderr)
#        elif ps.returncode != 0:
#            raise OSError(ps.returncode, stdout)
        passwd = pexpect.spawn("passwd %s" % username)
        for repeat in (1, 2):
            passwd.expect("password: ")
            passwd.sendline(user["password"])
            time.sleep(0.1)
        pw_entry = pwd.getpwnam(username)
    # potentially add the user to the desired (supplementary) group
    grp_entry = grp.getgrnam(config["group"])
    if not username in grp_entry.gr_mem:
        ps = subprocess.Popen(["usermod", "-aG", config["group"], username],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = ps.communicate()
        if stderr:
            raise OSError(ps.returncode, stderr)
        elif ps.returncode != 0:
            raise OSError(ps.returncode, stdout)
    # copy content of material_dir into user directory
    destination_path = os.path.join(pw_entry.pw_dir, config["tutorial_dir"])
    material = os.path.basename(config["material_dir"])
    if not material:
        material = os.path.dirname(config["material_dir"])
    try:
        tree_copy(config["material_dir"],
                os.path.join(destination_path, material))
    except shutil.Error:
        raise OSError(errno.ENOENT,
                "copying files for user '%s' failed" % username)
    # change the owner of the files in the user directory
    my_uid = os.getuid()
    my_gid = os.getgid()
    for (dirpath, dirnames, filenames) in os.walk(destination_path):
        stat = os.stat(dirpath)
        if stat.st_uid == my_uid or stat.st_gid == my_gid:
            os.chown(dirpath, pw_entry.pw_uid, pw_entry.pw_gid)
        for name in filenames:
            file_path = os.path.join(dirpath, name)
            stat = os.stat(file_path)
            if stat.st_uid == my_uid or stat.st_gid == my_gid:
                os.chown(file_path, pw_entry.pw_uid, pw_entry.pw_gid)

def parse_config(filename):
    """
    Handles parsing of the configuration file.
    """
    config = ConfigParser.SafeConfigParser(allow_no_value=True)
    config.read(filename)
    data = dict()
    data["students_list"] = config.get("Setup", "students_list")
    if not os.path.exists(data["students_list"]):
        raise IOError(errno.ENOENT, "No such file '%s'" % data["students_list"])
    data["tutorial_dir"] = config.get("Setup", "tutorial_dir")
    data["material_dir"] = config.get("Setup", "material_dir")
    if not os.path.exists(data["material_dir"]):
        raise IOError(errno.ENOENT,
                "No such directory '%s'" % data["material_dir"])
    data["passwd_length"] = config.getint("Setup", "password_length")
    data["group"] = config.get("Setup", "group")
    data["passwd_selection"] = string.printable[:63]
    return data


def main(argv):
    """
    Parse the student file, parse the configuration, adds the general usergroup,
    creates each student as a system user, writes out information.
    """
    # basic sanity checks
    if len(argv) == 1:
        config_file = str(argv[0])
    else:
        config_file = "notebooks.cfg"
    if not os.path.exists(config_file):
        raise IOError(errno.ENOENT, "No such file '%s'" % config_file)
    config = parse_config(config_file)
    # should add the group if it doesn't exist already
    try:
        ps = subprocess.Popen(["groupadd", "-f", config["group"]],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as err:
        print "\nDid you run this script with superuser privileges?\n"
        sys.exit(err.errno)
    (stdout, stderr) = ps.communicate()
    if stderr:
        print "\nDid you run this script with superuser privileges?\n"
        raise OSError(ps.returncode, stderr)
    elif ps.returncode != 0:
        print "\nDid you run this script with superuser privileges?\n"
        raise OSError(ps.returncode, stdout)
    # get the list of tutorial members
    with open(config["students_list"], "r") as file_handle:
        reader = csv.DictReader(file_handle)
        fieldnames = reader.fieldnames
        students = [row for row in reader]
    for user in students:
        create_user_environment(user, config)
    with open(config["students_list"], "w") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames)
        writer.writerow(dict(zip(fieldnames, fieldnames)))
        writer.writerows(students)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print "Usage:\nsudo python %s [config file: path]" % sys.argv[0]
        sys.exit(2)
    else:
        sys.exit(main(sys.argv[1:]))

