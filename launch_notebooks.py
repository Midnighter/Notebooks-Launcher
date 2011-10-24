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

    def get_local_ip():
        """
        This method works unreliably.
        """
        return [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]\
                if not ip.startswith("127.")]

    def get_network_ip():
        """
        Retrieve your network IP by opening a socket to google.

        May not find your public IP if you're behind NAT but often the network
        IP is just what we want.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('google.com', 0))
        return sock.getsockname()[0]

    def get_public_ip():
        """
        This finds your IP outside the local network and may require port
        forwarding from your router to the host machine.
        """
        import urllib2
        import re
        data = str(urllib2.urlopen("http://checkip.dyndns.com/").read())
        return re.search(r"Address: (\d+\.\d+\.\d+\.\d+)", data).group(1)

    config = ConfigParser.SafeConfigParser()
    config.read(filename)
    data = dict()
    data["students_list"] = config.get("Setup", "students_list")
    if not os.path.exists(data["students_list"]):
        raise IOError(errno.ENOENT, "No such file '%s'" % data["students_list"])
    data["tutorial_dir"] = config.get("Setup", "tutorial_dir")
    data["material_dir"] = config.get("Setup", "material_dir")
    data["launch_dir"] = config.get("Launch", "launch_dir")
    # if launch_dir was not given we simply use tutorial_dir/final_part_of_material_dir
    if not data["launch_dir"]:
        material = os.path.basename(data["material_dir"])
        if not material:
            material = os.path.dirname(data["material_dir"])
        data["launch_dir"] = os.path.join(data["tutorial_dir"], material)
    data["port"] = config.getint("Launch", "port")
    data["server"] = config.get("Launch", "server_address")
    # if no server was provided just use the ip of the localhost
    if not data["server"]:
        interfaces = get_local_ip()
        interfaces.append(get_network_ip())
        # if your webserver should be hosted for people outside your network,
        # you may uncomment the next line
#        interfaces.append(get_public_ip())
        data["server"] = str(interfaces[-1])
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
    if len(argv) == 1:
        config_file = str(argv[1])
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
    for (i, user) in enumerate(students):
        user["port"] = str(config["port"] + 1 + i)
        launch_user_instance(user, config)
    # save the student information
    with open(config["students_list"], "w") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames)
        writer.writerow(dict(zip(fieldnames, fieldnames)))
        writer.writerows(students)
    # generate webserver with content
    print "\nSpawning webserver at %s:%d\n" % (config["server"], config["port"])
    application = tornado.web.Application([(r"/", MainHandler,
            dict(title=config["title"], server=config["server"],
            students=students)),])
    application.listen(config["port"])
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print "Usage:\nsudo python %s [config file: path]" % sys.argv[0]
        sys.exit(2)
    else:
        sys.exit(main(sys.argv[1:]))

