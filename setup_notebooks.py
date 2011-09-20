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
#import logging


#logger = logging.getLogger(__name__)
#logger.setLevel(logging.INFO)
#logger.addHandler(logging.StreamHandler())


def tree_copy(src, dst):
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
    # check for existance of user
    name = user["email"].split("@")[0]
    name = name.split(".")
    username = "".join(name)
    try:
        pw_entry = pwd.getpwnam(username)
    except KeyError:
        # add a new user
        p = subprocess.Popen(["useradd", "-m", "-G", config.get("Setup",
                "group"), username],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        if stderr:
            raise OSError(p.returncode, stderr)
        elif p.returncode != 0:
            raise OSError(p.returncode, stdout)
        # set the (weak) password using numbers, letters, and the exclamation
        # mark
        user["password"] = "".join(random.choice(config["passwd_selection"]\
                for x in range(config["passwd_length"])))
        p = subprocess.Popen(["passwd", "--stdin", username],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate(user["password"])
        if stderr:
            raise OSError(p.returncode, stderr)
        elif p.returncode != 0:
            raise OSError(p.returncode, stdout)
        pw_entry = pwd.getpwnam(username)
    # potentially add the user to the desired (supplementary) group
    grp_entry = grp.getgrnam(config["group"])
    if not username in grp_entry.gr_mem:
        p = subprocess.Popen(["usermod", "-aG", config["group"], username],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        if stderr:
            raise OSError(p.returncode, stderr)
        elif p.returncode != 0:
            raise OSError(p.returncode, stdout)
    # copy content of material_dir into user directory
    destination_path = os.path.join(pw_entry.pw_dir, config["tutorial_dir"])
    material = os.path.basename(config["material_dir"])
    if not material:
        material = os.path.dirname(config["material_dir"])
    try:
        tree_copy(config["material_dir"], os.path.join(destination_path, material))
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
    config = ConfigParser.SafeConfigParser(allow_no_value=True)
    config.read(filename)
    data = dict()
    data["tutorial_dir"] = config.get("Setup", "tutorial_dir")
    if not os.path.exists(data["tutorial_dir"]):
        raise IOError(errno.ENOENT,
                "No such directory '%s'" % data["tutorial_dir"])
    data["material_dir"] = config.get("Setup", "material_dir")
    if not os.path.exists(data["material_dir"]):
        raise IOError(errno.ENOENT,
                "No such directory '%s'" % data["material_dir"])
    data["passwd_length"] = config.getint("Setup", "password_length")
    data["group"] = config.get("Setup", "group")
    data["passwd_selection"] = string.printable[:63]
    return data


def main(argv):
    # basic sanity checks
    if len(argv) >= 1:
        filename = str(argv[0])
    else:
        filename = "students.csv"
    if not os.path.exists(filename):
        raise IOError(errno.ENOENT, "No such file '%s'" % filename)
    if len(argv) == 2:
        config_file = str(argv[1])
    else:
        config_file = "notebooks.cfg"
    if not os.path.exists(config_file):
        raise IOError(errno.ENOENT, "No such file '%s'" % config_file)
    config = parse_config(config_file)
    # should add the group if it doesn't exist already
    try:
        p = subprocess.Popen(["groupadd", "-f", config.get("Setup", "group")],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as err:
        print "Did you run this script with superuser privileges?"
        sys.exit(err.errno)
    (stdout, stderr) = p.communicate()
    if stderr:
        raise OSError(p.returncode, stderr)
    elif p.returncode != 0:
        raise OSError(p.returncode, stdout)
    # get the list of tutorial members
    with open(filename, "r") as file_handle:
        reader = csv.DictReader(file_handle)
        fieldnames = reader.fieldnames
        students = [row for row in reader]
    for user in students:
        create_user_environment(user, config)
    with open(filename, "w") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames)
        writer.writerow(dict(zip(fieldnames, fieldnames)))
        writer.writerows(students)


if __name__ == "__main__":
    if len(sys.argv) < 1 or len(sys.argv) > 3:
        print "Usage:\nsudo python %s [student list: path [config file: path]]"\
                % sys.argv[0]
        sys.exit(2)
    else:
        sys.exit(main(sys.argv[1:]))

