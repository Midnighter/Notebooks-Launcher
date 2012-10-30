# -*- coding: utf-8 -*-


"""
===========================
Utility Functions for Linux
===========================

:Author:
    Moritz Emanuel Beber
:Date:
    2012-10-30
:Copyright:
    Copyright(c) 2012 Jacobs University of Bremen. All rights reserved.
:File:
    genericutils.py
"""


import os
import logging
import subprocess
import codecs
import csv
import socket
import errno
import string
import shutil
import ConfigParser

from IPython.utils.path import get_ipython_dir


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

    Parameters
    ----------
    uid: `int`
        User ID under which a function will be run.
    gid: `int`
        Group ID under which a function will be run.
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
        err = subprocess.CalledProcessError(prcs.returncode, args)
        err.output = stderr
        raise err
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
        err = subprocess.CalledProcessError(prcs.returncode, args)
        err.output = stderr
        raise err
    return stdout if stdout else stderr

def ipython_dir_command():
    print(get_ipython_dir())

