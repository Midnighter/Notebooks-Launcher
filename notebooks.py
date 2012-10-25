#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
======================================
Configure IPython Notebook Environment
======================================

:Author:
    Moritz Emanuel Beber
:Date:
    2011-12-31
:Copyright:
    Copyright(c) 2011 Jacobs University of Bremen. All rights reserved.
:File:
    notebooks.py
"""


__all__ = ["execute_command", "launch_as"]


import logging
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
import codecs
import socket

from glob import glob

if os.uname()[0] == "Linux":
    from linux_utils import add_user, add_group, add_password, append_to_group,\
            kill_process, delete_user, delete_group
elif os.uname()[0] == "Darwin":
    from mac_utils import add_user, add_group, add_password, append_to_group,\
            kill_process, delete_user, delete_group
else:
    raise StandardError("unkown operating system")

# non-standard but must for ipython notebook
import tornado.ioloop
import tornado.web
import tornado.template

from IPython.utils.path import get_ipython_dir
from IPython.lib import passwd


################################################################################
# Utility
################################################################################


LOGGER = logging.getLogger()


# expected header for the user database file
FIELDNAMES = ["name", "surname", "username", "email", "sys-pass", "nb-pass", "port"]


def read_database(filename, enc="utf-8"):
    """
    Reads a spreadsheet-like file with user information.

    Parameters
    ----------
    filename: `str`
        System path that specifies the file location.
    enc: `str` (optional)
        The encoding of the specified file.

    Warnings
    --------
    The `csv` reader may have issues with UTF-16 encoded files.
    """
    global FIELDNAMES
#    sniffer = csv.Sniffer()
    with codecs.open(filename, "rb", encoding=enc) as file_handle:
#        local_dialect = sniffer.sniff(file_handle.readline(), delimiters=u",;:\t")
        local_dialect = csv.excel
#        file_handle.seek(0)
        reader = csv.DictReader(file_handle, dialect=local_dialect)
        if set(FIELDNAMES).issubset(set(reader.fieldnames)):
            FIELDNAMES = reader.fieldnames
        else:
            raise ValueError(u"database file lacks required field names:\n"\
                    u"\theader format should be '{0}'"\
                    .format(",".join(FIELDNAMES)))
        users = [row for row in reader]
    return (users, local_dialect)

def write_database(filename, users, local_dialect="excel", enc="utf-8"):
    """
    Writes a spreadsheet-like file with user information.

    Parameters
    ----------
    filename: `str`
        System path that specifies where the file should be written.
    users: `list`
        List whose elements are one `dict` per user. Keywords correspond to
        field names and values are entries.
    local_dialect: `csv.Dialect` or `str` (optional)
        Can be a `csv.Dialect` instance or a string specifying the dialect used.
    enc: `str` (optional)
        The encoding of the specified file.

    Warnings
    --------
    If a user `dict` contains a key that is not in the standard header, writing
    will fail and all file contents except for the header are lost.
    """
    with codecs.open(filename, "wb", encoding=enc) as file_handle:
        writer = csv.DictWriter(file_handle, FIELDNAMES, dialect=local_dialect)
        writer.writerow(dict(zip(FIELDNAMES, FIELDNAMES)))
        writer.writerows(users)

def parse_config(filename, enc="utf-8"):
    """
    Handles parsing of the configuration file.

    Parameters
    ----------
    filename: `str`
        System path that specifies the file location.
    enc: `str` (optional)
        The encoding of the specified file.
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
        try:
            sock.connect(("gmail.com", 80))
            address = sock.getsockname()[0]
        except (socket.error, socket.gaierror, socket.timeout):
            LOGGER.debug(u"pssst:", exc_info=True)
            address = "127.0.0.1"
        finally:
            sock.close()
        return address

    def get_public_ip():
        """
        This finds your IP outside the local network and may require port
        forwarding from your router to the host machine.
        """
        import urllib2
        import re
        data = str(urllib2.urlopen("http://whatismyip.org").read())
        return re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", data).group(1)

    config = ConfigParser.SafeConfigParser()
    with codecs.open(filename, encoding=enc) as file_handle:
        config.readfp(file_handle)
    data = dict()
    # setup related options
    data["user list"] = config.get("Setup", "user_list")
    if not os.path.exists(data["user list"]):
        raise IOError(errno.ENOENT, u"no such file '{0}'"\
                .format(data["user list"]))
    data["tutorial dir"] = config.get("Setup", "tutorial_dir")
    data["material dir"] = config.get("Setup", "material_dir")
    if not os.path.exists(data["material dir"]):
        raise IOError(errno.ENOENT,
                u"no such directory '{0}'".format(data["material dir"]))
    data["passwd length"] = config.getint("Setup", "password_length")
    data["group"] = config.get("Setup", "group")
    data["passwd selection"] = string.printable[:62]
    data["profile"] = config.get("Setup", "profile")
    # launch related options
    data["certificate"] = config.get("Launch", "cert_file")
    if not os.path.isabs(data["certificate"]):
        raise ValueError(u"path to certificate file '{0}' is not absolute"\
                .format(data["certificate"]))
    if not os.path.exists(data["certificate"]):
        raise IOError(errno.ENOENT, u"no such directory '{0}'"\
                .format(data["certificate"]))
    data["launch dir"] = config.get("Launch", "launch_dir")
    # if launch_dir was not given we simply use tutorial_dir/final_part_of_material_dir
    if not data["launch dir"]:
        material = os.path.basename(data["material dir"])
        if not material:
            material = os.path.dirname(data["material dir"])
        data["launch dir"] = os.path.join(data["tutorial dir"], material)
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
    # shutdown related options
    data["storage dir"] = config.get("Shutdown", "storage_dir")
    data["owner"] = config.get("Shutdown", "owner")
    return data

def tree_copy(src, dst):
    """
    Iteratively copies a folder structure to a destination rooted somewhere
    else.

    Parameters
    ----------
    src: `str`
        Root of the file path hierarchy that is to be copied elsewhere.
    dst: `str`
        File path to which the source tree is added.

    Notes
    -----
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

def tree_chown(pw_entry, root):
    """
    Iteratively descends a directory structure and changes the owner of all
    files and directories.

    Parameters
    ----------
    pw_entry: `passwd` entry
        A user entry of the `passwd` database accessed through the `pwd` module.
    root: `str`
        Root of the file path hierarchy whose owner should be changed.

    Notes
    -----
    Ignores symlinks and mount points.
    """
    for (dirpath, dirnames, filenames) in os.walk(root):
        stat = os.stat(dirpath)
        if stat.st_uid != pw_entry.pw_uid or stat.st_gid != pw_entry.pw_gid:
            os.chown(dirpath, pw_entry.pw_uid, pw_entry.pw_gid)
        for name in filenames:
            file_path = os.path.join(dirpath, name)
            stat = os.stat(file_path)
            if stat.st_uid != pw_entry.pw_uid or stat.st_gid != pw_entry.pw_gid:
                os.chown(file_path, pw_entry.pw_uid, pw_entry.pw_gid)

def assume_user(uid, gid):
    """
    Simple helper that returns a function that will be called by subprocess
    pipes just prior to executing their command.
    """
    def result():
        os.setgid(gid)
        os.setuid(uid)
    return result

def launch_as(pw_entry, args, cwd, stdin=None):
    """
    Execute a command under a different user.

    Parameters
    ----------
    pw_entry: `passwd` entry
        A user entry of the `passwd` database accessed through the `pwd` module.
    args: `list`
        A list passed to subprocess that specifies the command.
    cwd: `str`
        Current working directory for the command to be executed in.
    stdin: `str` (optional)
        Optional input for the external command.
    """
    env = os.environ.copy()
    env["HOME"] = pw_entry.pw_dir
    env["LOGNAME"] = pw_entry.pw_name
    env["PWD"] = cwd
    env["USER"] = pw_entry.pw_name
    # should not fail
    prcs = subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=assume_user(pw_entry.pw_uid, pw_entry.pw_gid))
    (stdout, stderr) = prcs.communicate(stdin)
    if prcs.returncode != 0:
        raise subprocess.CalledProcessError(prcs.returncode, args, stderr)
    return stdout if stdout else stderr

def execute_command(args, stdin=None, cwd=None, env=None):
    """
    Execute a system command.

    Parameters
    ----------
    args: `list`
        A list passed to subprocess that specifies the command.
    stdin: `str` (optional)
        Optional input for the external command.
    cwd: `str` (optional)
        Current working directory for the command to be executed in.
    env: dict (optional)
        A dictionary with the system environment that should replace the current
        user's.
    """
    prcs = subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    (stdout, stderr) = prcs.communicate(stdin)
    if prcs.returncode != 0:
        raise subprocess.CalledProcessError(prcs.returncode, args, stderr)
    return stdout if stdout else stderr


################################################################################
# Setup
################################################################################


def create_user_environment(user, config):
    """
    Sets up the user working directories needed.

    Creates a user account if necessary, creates a password for it, adds it to
    a general usergroup, copies specified material into the user directory, and
    makes the user the owner of those files and directories.
    """
    # check for existance of user
    try:
        pw_entry = pwd.getpwnam(user["username"])
    except KeyError:
        # add a new user
        rc = add_user(user["username"], config["group"])
        if rc != 0:
            return rc
        # set the (weak) password using numbers, letters, and the exclamation
        # mark
        if not user["sys-pass"]:
            user["sys-pass"] = u"".join(random.choice(config["passwd selection"])\
                    for x in range(config["passwd length"]))
            rc = add_password(user["username"], user["sys-pass"])
            if rc != 0:
                return rc
    # should not fail now
    pw_entry = pwd.getpwnam(user["username"])
    # potentially add the user to the desired (supplementary) group
    grp_entry = grp.getgrnam(config["group"])
    if not user["nb-pass"]:
        user["nb-pass"] = u"".join(random.choice(config["passwd selection"])\
                for x in range(config["passwd length"]))
    if not user["username"] in grp_entry.gr_mem:
        append_to_group(config["group"], user["username"])
    # create the ipython config
    cmd = ["ipython", "profile", "create", config["profile"]]
    try:
        launch_as(pw_entry, cmd, pw_entry.pw_dir)
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        return err.returncode
    # location of the ipython directory created with the profile
    # get_ipython_dir currently returns different results for other users :S
    cmd = ["python", "ipython_dir.py"]
    user_ipython_dir = launch_as(pw_entry, cmd, os.getcwd()).strip()
    # if the specified profile exists we copy the contents
    profile = "profile_{0}".format(config["profile"])
    prfl_loc = os.path.join(get_ipython_dir(), profile)
    usr_prfl_loc = os.path.join(user_ipython_dir, profile)
    if os.path.exists(prfl_loc):
        # copy profile files
        for filename in glob(os.path.join(prfl_loc, "*.py")):
            shutil.copy2(filename, usr_prfl_loc)
            dst_file = os.path.join(usr_prfl_loc, os.path.basename(filename))
            os.chown(dst_file, pw_entry.pw_uid, pw_entry.pw_gid)
        # copy startup files
        for filename in glob(os.path.join(prfl_loc, "startup", "*.py")):
            shutil.copy2(filename, usr_prfl_loc)
            dst_file = os.path.join(usr_prfl_loc, os.path.basename(filename))
            os.chown(dst_file, pw_entry.pw_uid, pw_entry.pw_gid)
    password = passwd(user["nb-pass"])
    location = os.path.join(usr_prfl_loc, u"ipython_notebook_config.py")
    with codecs.open(location, "rb", encoding="utf-8") as file_handle:
        content = file_handle.readlines()
    for (i, line) in enumerate(content):
        if line.find(u"c.NotebookApp.password") > -1:
            break
    content[i] = u"c.NotebookApp.password = u'{0}'".format(password)
    with codecs.open(location, "wb", encoding="utf-8") as file_handle:
        file_handle.writelines(content)
    # copy content of material dir into user directory
    destination_path = os.path.normpath(os.path.join(pw_entry.pw_dir,
            config["tutorial dir"]))
    material = os.path.basename(config["material dir"])
    if not material:
        material = os.path.dirname(config["material dir"])
    try:
        tree_copy(config["material dir"],
                os.path.join(destination_path, material))
    except shutil.Error:
        raise OSError(errno.ENOENT,
                u"copying files for user '{0}' failed".format(user["username"]))
    # change the owner of the files in the user directory
    tree_chown(pw_entry, destination_path)

def setup(config, users):
    """
    Parse the student file, parse the configuration, adds the general usergroup,
    creates each student as a system user, writes out information.
    """
    # should add the group if it doesn't exist already
    rc = add_group(config["group"])
    if rc != 0:
        raise OSError("failed to add new group '{0}'".format(config["group"]))
    # create users in the list
    for usr in users:
        if create_user_environment(usr, config) > 0:
            LOGGER.warn(u"Failed to setup environment for user '{0}'.".format(
                    usr["username"]))
        else:
            LOGGER.info(u"Setup environment for user '{0}'."\
                    .format(usr["username"]))


################################################################################
# Launch
################################################################################


class MainHandler(tornado.web.RequestHandler):
    """
    Tornado webserver subclass.

    An instance of this class can be bound to an address and port and it will
    handle http requests to those.
    """

    def initialize(self, title, server, users):
        """
        This method negates the need for an __init__ method.
        """
        loader = tornado.template.Loader(os.getcwd())
        self.content = loader.load("template.html").generate(mytitle=title,
                server_adress=server, users=users)

    def get(self):
        """
        Any http get requests will call this method.
        """
        self.write(self.content)


def launch_user_instance(user, config):
    """
    Launches an IPython Notebook for a specified user in an environment defined
    by config.
    """
    # must not fail, should have been taken care of by setup script
    pw_entry = pwd.getpwnam(user["username"])
    # assume student user status and launch notebook
    # because the notebook kernel runs inside of screen we cannot catch errors
    # (unless we pipe the output into a file or we could pipe the commands and
    # then detach, TODO)
    args = ["screen", "-dmS", user["username"],
            "ipython", "notebook",
            "--ip", "'*'",
            "--port", user["port"],
            "--certfile", config["certificate"],
            "--profile", config["profile"],
#            "--pylab", "inline",
            "--no-browser"]
    cwd = os.path.join(pw_entry.pw_dir, config["launch dir"])
    # should not fail
    launch_as(pw_entry, args, cwd)

def launch(config, users):
    """
    Start notebook kernels for each user and launch a website from which to
    reach them.

    Notes
    -----
    This process will continue to run indefinitely, ending it will cause the
    webserver to be shut down but the notebook kernels to continue running.
    """
    # launch per-user notebook kernels
    for (i, usr) in enumerate(users):
        usr["port"] = str(config["port"] + 1 + i)
        launch_user_instance(usr, config)
        LOGGER.info(u"Started notebook kernel(s) for user '{0}'."\
                .format(usr["username"]))
    # generate webserver with content
    LOGGER.warn("\nSpawning webserver at {0}:{1}\n".format(config["server"],
            config["port"]))
    application = tornado.web.Application([(r"/", MainHandler,
            dict(title=config["title"], server=config["server"],
            users=users)),])
    application.listen(config["port"])
    tornado.ioloop.IOLoop.instance().start()


################################################################################
# Shut Down
################################################################################


def kill_notebooks(user, config):
    """
    Finds IPython Notebook instances running for the user and kills them.
    """
    # must not fail, i.e., user must exist on the system
    rc = kill_process(user["username"], "ipython notebook")
    # retrieve user generated material
    try:
        pw_entry = pwd.getpwnam(user["username"])
    except KeyError:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(u"Failed to get passwd entry for '{0}'."\
                .format(user["username"]))
        return
    source_path = os.path.normpath(os.path.join(pw_entry.pw_dir,
            config["tutorial dir"]))
    material = os.path.basename(config["material dir"])
    if not material:
        material = os.path.dirname(config["material dir"])
    dest_path = os.path.join(config["storage dir"], user["username"])
    try:
        tree_copy(source_path, dest_path)
    except shutil.Error:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(u"Retrieving files for user '{0}' failed."\
                .format(user["username"]))
    user["port"] = u""

def shutdown(config, users):
    """
    Shutdown each user's notebook kernel and retrieve their existing material.
    """
    for usr in users:
        kill_notebooks(usr, config)
        LOGGER.info(u"Shutdown notebook kernel(s) for user '{0}'."\
                .format(usr["username"]))
    # change the owner of the files in the storage directory
    try:
        owner_entry = pwd.getpwnam(config["owner"])
    except KeyError:
        LOGGER.warn(u"Failed to get passwd entry for owner '{0}',"\
                u" did you set it in the config file?".format(config["owner"]))
        return
    tree_chown(owner_entry, config["storage dir"])


################################################################################
# Remove
################################################################################


def remove(config, users):
    """
    Remove all files and accounts of users listed in the database file.
    """
    for usr in users:
        delete_user(usr)
    choice = raw_input("Do you really want to remove the group '{0}'? (y/[n]):"\
            .format(config["group"]))
    if choice.lower() == "y":
        delete_group(config["group"])


################################################################################
# Main
################################################################################


def main(argv):
    LOGGER.setLevel(logging.INFO)
    LOGGER.setLevel(logging.DEBUG)
    LOGGER.addHandler(logging.StreamHandler())
    # basic sanity checks
    # check for privileges
    if os.geteuid() != 0:
        raise StandardError("You need to have superuser privileges to run this script.")
    # existance of config file
    if len(argv) == 2:
        config_file = argv[1]
    else:
        config_file = u"notebooks.cfg"
    if not os.path.exists(config_file):
        raise IOError(errno.ENOENT, u"no such file '{0}'".format(config_file))
    # parse configuration
    config = parse_config(config_file)
    # get the list of notebook users
    (users, csv_dialect) = read_database(config["user list"])
    try:
        # call appropriate function
        if argv[0].lower() == "setup":
            setup(config, users)
        elif argv[0].lower() == "launch":
            launch(config, users)
        elif argv[0].lower() == "shutdown":
            shutdown(config, users)
        elif argv[0].lower() == "remove":
            remove(config, users)
        else:
            raise ValueError(u"unrecognised option: '{0}'".format(argv[0]))
    except BaseException as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        raise err
    finally:
        # write user information
        write_database(config["user list"], users, csv_dialect)


if __name__ == "__main__":
    argc = len(sys.argv)
    if argc < 2 or argc > 3:
        LOGGER.critical(u"Usage:\nsudo python {0} <setup | launch | shutdown | remove>"\
                u" [config file: path]".format(sys.argv[0]))
        sys.exit(2)
    try:
        rec = main(sys.argv[1:])
    except (Exception) as err:
        rec = err.errno if hasattr(err, "errno") else 1
        LOGGER.critical(str(err))
    finally:
        # perform clean-up
        logging.shutdown()
    sys.exit(rec)

