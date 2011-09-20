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


def kill_notebooks(user):
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
    elif p2.returncode != 0:
        raise OSError(p2.returncode, stdout)
    stdout = stdout.split("\n")
    for line in stdout:
        try:
            os.kill(int(line.split()[0]), signal.SIGHUP)
        except ValueError:
            continue
        except IndexError:
            break
    user["port"] = ""

def main(argv):
    # basic sanity checks
    if len(argv) >= 1:
        filename = str(argv[0])
    else:
        filename = "students.csv"
    if not os.path.exists(filename):
        raise IOError(errno.ENOENT, "No such file '%s'" % filename)
    # get the list of tutorial members
    with open(filename, "r") as file_handle:
        reader = csv.DictReader(file_handle)
        fieldnames = reader.fieldnames
        students = [row for row in reader]
    for user in students:
        kill_notebooks(user)
    # save the student information
    with open(filename, "w") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames)
        writer.writerow(dict(zip(fieldnames, fieldnames)))
        writer.writerows(students)


if __name__ == "__main__":
    if len(sys.argv) < 1 or len(sys.argv) > 2:
        print "Usage:\nsudo python %s [student list: path]" % sys.argv[0]
        sys.exit(2)
    else:
        sys.exit(main(sys.argv[1:]))

