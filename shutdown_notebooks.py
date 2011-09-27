#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
==========================
Shutdown IPython Notebooks
==========================

:Author:
    Moritz Emanuel Beber
:Date:
    2011-09-12
:Copyright:
    Copyright(c) 2011 Jacobs University of Bremen. All rights reserved.
:File:
    shutdown_notebooks.py
"""


import sys
import os
import signal
import csv
import errno
import subprocess
import ConfigParser


def kill_notebooks(user):
    """
    Finds IPython Notebook instances running for the user and kills them.
    """
    # check for existance of user
    name = user["email"].split("@")[0]
    name = name.split(".")
    username = "".join(name)
    # must not fail, i.e., user must exist on the system
    ps = subprocess.Popen(["ps", "-u", username, "-o", "pid,command"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p1 = subprocess.Popen(["grep", "ipython notebook"], stdin=ps.stdout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p2 = subprocess.Popen(["grep", "-v", "grep"], stdin=p1.stdout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ps.stdout.close()
    ps.stderr.close()
    p1.stdout.close()
    p1.stderr.close()
    (stdout, stderr) = p2.communicate()
    if stderr:
        raise OSError(p2.returncode, stderr)
    elif stdout and p2.returncode != 0:
        raise OSError(p2.returncode, stdout)
    elif p2.returncode == 0:
        stdout = stdout.split("\n")
        for line in stdout:
            try:
                os.kill(int(line.split()[0]), signal.SIGHUP)
            except (OSError, ValueError):
                continue
            except IndexError:
                break
    user["port"] = ""

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
    return data


def main(argv):
    """
    Parses student file, kills IPython Notebooks of each student, and writes out
    information.
    """
    # basic sanity checks
    if len(argv) == 1:
        config_file = str(argv[0])
    else:
        config_file = "notebooks.cfg"
    if not os.path.exists(config_file):
        raise IOError(errno.ENOENT, "No such file '%s'" % config_file)
    config = parse_config(config_file)
    # get the list of tutorial members
    with open(config["students_list"], "r") as file_handle:
        reader = csv.DictReader(file_handle)
        fieldnames = reader.fieldnames
        students = [row for row in reader]
    for user in students:
        kill_notebooks(user)
    # save the student information
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

