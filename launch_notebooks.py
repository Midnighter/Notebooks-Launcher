#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
=================================================
Launch IPython Notebook Environment and Webserver
=================================================

:Author:
    Moritz Emanuel Beber
:Date:
    2011-09-01
:Copyright:
    Copyright(c) 2011 Jacobs University of Bremen. All rights reserved.
:File:
    launch_notebooks.py
"""


import sys
import os
import pwd
import subprocess
import csv
import socket
import errno
import ConfigParser
import tornado.ioloop
import tornado.web
import tornado.template


class MainHandler(tornado.web.RequestHandler):
    """
    Tornado webserver subclass.

    An instance of this class can be bound to an address and port and it will
    handle http requests to those.
    """

    def initialize(self, title, server, students):
        """
        This method negates the need for an __init__ method.
        """
        loader = tornado.template.Loader(os.getcwd())
        self.content = loader.load("template.html").generate(mytitle=title,
                server_adress=server, students=students)

    def get(self):
        """
        Any http get requests will call this method.
        """
        self.write(self.content)


def assume_user(uid, gid):
    """
    Simple helper that returns a function that will be called by subprocess
    pipes just prior to executing their command.
    """
    def result():
        os.setgid(gid)
        os.setuid(uid)
    return result

def launch_user_instance(user, config):
    """
    Launches an IPython Notebook for a specified user in an environment defined
    by config.
    """
    # check for existance of user
    name = user["email"].split("@")[0]
    name = name.split(".")
    username = "".join(name)
    # must not fail, should have been taken care of by setup script
    pw_entry = pwd.getpwnam(username)
    # assume student user status and launch notebook
    args = ["screen", "-dmS", username,
            "ipython", "notebook",
            "--pylab=inline",
            "--IPythonNotebookApp.ws_hostname=%s" % config["server"],
            "--IPythonNotebookApp.ip=%s" % config["server"],
            "--port=%s" % user["port"]]
    cwd = os.path.join(pw_entry.pw_dir, config["launch_dir"])
    env = os.environ.copy()
    env["HOME"] = pw_entry.pw_dir
    env["LOGNAME"] = pw_entry.pw_name
    env["PWD"] = cwd
    env["USER"] = pw_entry.pw_name
    # should not fail
    subprocess.check_call(args, cwd=cwd, env=env,
            preexec_fn=assume_user(pw_entry.pw_uid, pw_entry.pw_gid))

def parse_config(filename):
    """
    Handles parsing the configuration file and sets some default values.
    """
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
    data["launch_dir"] = config.get("Launch", "launch_dir")
    # if launch_dir was not given we simply use tutorial_dir/material_dir
    if not data["launch_dir"]:
        material = os.path.basename(config["material_dir"])
        if not material:
            material = os.path.dirname(config["material_dir"])
        data["launch_dir"] = os.path.join(data["tutorial_dir"], material)
    data["port"] = config.getint("Launch", "port")
    data["server"] = config.get("Launch", "server_address")
    # if no server was provided just use the ip of the localhost
    if not data["server"]:
        interfaces = [ip for ip in\
                socket.gethostbyname_ex(socket.gethostname())[2]\
                if not ip == "127.0.0.1"]
        data["server"] = str(interfaces[0])
    data["title"] = config.get("Launch", "web_title")
    return data


def main(argv):
    """
    Parse students, parse configuration, launch notebook for each student, write
    back information, and launch webserver.

    Maybe the webserver could be deamonized but I like having the output in a
    'screen' instance, for example.
    """
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
    # get the list of tutorial members
    with open(filename, "r") as file_handle:
        reader = csv.DictReader(file_handle)
        fieldnames = reader.fieldnames
        students = [row for row in reader]
    for (i, user) in enumerate(students):
        user["port"] = str(config["port"] + 1 + i)
        launch_user_instance(user, config)
    # save the student information
    with open(filename, "w") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames)
        writer.writerow(dict(zip(fieldnames, fieldnames)))
        writer.writerows(students)
    # generate webserver with content
    application = tornado.web.Application([(r"/", MainHandler,
            dict(title=config["title"], server=config["server"],
            students=students)),])
    application.listen(config["port"])
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    if len(sys.argv) < 1 or len(sys.argv) > 3:
        print "Usage:\nsudo python %s [student list: path [config file: path]]"\
                % sys.argv[0]
        sys.exit(2)
    else:
        sys.exit(main(sys.argv[1:]))

