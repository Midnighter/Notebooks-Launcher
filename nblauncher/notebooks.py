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


import logging
import sys
import os
import shutil
import pwd
import grp
import subprocess
import errno
import random
import codecs

import nblauncher.genericutils as gutil

if os.uname()[0] == "Linux":
    import nblauncher.linuxutils as usrt
elif os.uname()[0] == "Darwin":
    import nblauncher.macutils as usrt
else:
    raise StandardError("unkown operating system")

from glob import glob

# non-standard but must for ipython notebook
import tornado.ioloop
import tornado.web
import tornado.template

from IPython.utils.path import get_ipython_dir
from IPython.lib import passwd


LOGGER = logging.getLogger()


################################################################################
# Setup
################################################################################


def create_user_environment(user, config):
    """
    Sets up the user working directories as needed.

    Creates a user account if necessary, creates a password for it, adds it to
    a general usergroup, creates an IPython profile, and makes the user the
    owner of those files and directories.

    Parameters
    ----------
    user: `dict`
        A dictionary as parsed from the database describing a user.
    config: `dict`
        A dictionary as parsed from the configuration file.
    """
    # check for existance of user
    try:
        pw_entry = pwd.getpwnam(user["username"])
    except KeyError:
        # add a new user
        rc = usrt.add_user(user["username"], [config["group"]])
        if rc != 0:
            return rc
        # set the (weak) password using numbers, letters, and the exclamation
        # mark
        if not user["sys-pass"]:
            user["sys-pass"] = u"".join(random.choice(config["passwd selection"])\
                    for x in range(config["passwd length"]))
            rc = usrt.add_password(user["username"], user["sys-pass"])
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
        usrt.append_to_group(config["group"], user["username"])
    # create the ipython config
    cmd = ["ipython", "profile", "create", config["profile"]]
    try:
        gutil.launch_as(pw_entry, cmd, pw_entry.pw_dir)
    except subprocess.CalledProcessError as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(err.output.strip())
        return err.returncode
    # location of the ipython directory created with the profile
    # get_ipython_dir currently returns different results for other users :S
    cmd = ["ipython_dir"]
    user_ipython_dir = gutil.launch_as(pw_entry, cmd, os.getcwd()).strip()
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
    if content:
        i = 0
        for (i, line) in enumerate(content):
            if line.find(u"c.NotebookApp.password") > -1:
                break
        content[i] = u"c.NotebookApp.password = u'{0}'".format(password)
    with codecs.open(location, "wb", encoding="utf-8") as file_handle:
        file_handle.writelines(content)

def setup(config, users):
    """
    Adds a general usergroup, creates each student as a system user, creates
    IPython profile.

    Parameters
    ----------
    config: `dict`
        A dictionary as parsed from the configuration file.
    users: `list`
        A list of dictionaries as parsed from the database describing individual
        users.
    """
    # should add the group if it doesn't exist already
    rc = usrt.add_group(config["group"])
    if rc != 0:
        raise OSError("failed to add new group '{0}'".format(config["group"]))
    # create users in the list
    # mac hack, because mac pwd database does not update
    for usr in users:
        if create_user_environment(usr, config) > 0:
            LOGGER.warn(u"Failed to setup environment for user '{0}'.".format(
                    usr["username"]))
        else:
            send_out(usr, config)
            LOGGER.info(u"Setup environment for user '{0}'."\
                    .format(usr["username"]))


################################################################################
# Send
################################################################################


def send_out(user, config):
    """
    Copies material to user account and makes the user owner of it.

    Parameters
    ----------
    user: `dict`
        A dictionary as parsed from the database describing a user.
    config: `dict`
        A dictionary as parsed from the configuration file.
    """
    # must not fail
    pw_entry = pwd.getpwnam(user["username"])
    # copy content of material dir into user directory
    destination_path = os.path.normpath(os.path.join(pw_entry.pw_dir,
            config["tutorial dir"]))
    material = os.path.basename(config["material dir"])
    if not material:
        material = os.path.dirname(config["material dir"])
    try:
        gutil.interactive_tree_copy(config["material dir"],
                os.path.join(destination_path, material))
    except shutil.Error:
        raise OSError(errno.ENOENT,
                u"copying files for user '{0}' failed".format(user["username"]))
    # change the owner of the files in the user directory
    gutil.tree_chown(pw_entry, destination_path)

def send(config, users):
    """
    Copy course material to user accounts.

    Parameters
    ----------
    config: `dict`
        A dictionary as parsed from the configuration file.
    users: `list`
        A list of dictionaries as parsed from the database describing individual
        users.
    """
    for usr in users:
        try:
            send_out(usr, config)
            LOGGER.info(u"Sent material to user '{0}'.".format(usr["username"]))
        except OSError:
            LOGGER.debug(u"pssst:", exc_info=True)
            LOGGER.warn(u"Sending files to user '{0}' failed."\
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

    Parameters
    ----------
    user: `dict`
        A dictionary as parsed from the database describing a user.
    config: `dict`
        A dictionary as parsed from the configuration file.
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
    gutil.launch_as(pw_entry, args, cwd)

def launch(config, users):
    """
    Start notebook kernels for each user and launch a website from which to
    reach them.

    Parameters
    ----------
    config: `dict`
        A dictionary as parsed from the configuration file.
    users: `list`
        A list of dictionaries as parsed from the database describing individual
        users.

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


def shutdown(config, users):
    """
    Shutdown each user's notebook kernel(s).

    Parameters
    ----------
    config: `dict`
        A dictionary as parsed from the configuration file.
    users: `list`
        A list of dictionaries as parsed from the database describing individual
        users.
    """
    for usr in users:
        usrt.kill_process(usr["username"], "ipython notebook")
        LOGGER.info(u"Shutdown notebook kernel(s) for user '{0}'."\
                .format(usr["username"]))


################################################################################
# Retrieve
################################################################################


def retrieve_from(user, config):
    """
    Retrieve all data in the material directory of the user.

    Parameters
    ----------
    user: `dict`
        A dictionary as parsed from the database describing a user.
    config: `dict`
        A dictionary as parsed from the configuration file.
    """
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
        gutil.tree_copy(source_path, dest_path)
    except shutil.Error:
        LOGGER.debug(u"pssst:", exc_info=True)
        LOGGER.warn(u"Retrieving files for user '{0}' failed."\
                .format(user["username"]))
    user["port"] = u""
    # change the owner of the files in the storage directory
    try:
        owner_entry = pwd.getpwnam(config["owner"])
    except KeyError:
        LOGGER.warn(u"Failed to get passwd entry for owner '{0}',"\
                u" did you set it in the config file?".format(config["owner"]))
        return
    gutil.tree_chown(owner_entry, dest_path)

def retrieve(config, users):
    """
    Retrieve created files from users.

    Parameters
    ----------
    config: `dict`
        A dictionary as parsed from the configuration file.
    users: `list`
        A list of dictionaries as parsed from the database describing individual
        users.
    """
    for usr in users:
        retrieve_from(usr, config)
        LOGGER.info(u"Retrieved files from user '{0}'.".format(usr["username"]))


################################################################################
# Remove
################################################################################


def remove(config, users):
    """
    Remove all files and accounts of users listed in the database file.

    Parameters
    ----------
    config: `dict`
        A dictionary as parsed from the configuration file.
    users: `list`
        A list of dictionaries as parsed from the database describing individual
        users.
    """
    choice = raw_input("Do you really want to remove the users '{0}'? (y/[n]):"\
            .format(", ".join(usr["username"] for usr in users)))
    if choice.lower() == "y":
        for usr in users:
            retrieve_from(usr, config)
            rc = usrt.delete_user(usr["username"])
            if rc == 0:
                usr["sys-pass"] = ""
                usr["nb-pass"] = ""
    choice = raw_input("Do you really want to remove the group '{0}'? (y/[n]):"\
            .format(config["group"]))
    if choice.lower() == "y":
        usrt.delete_group(config["group"])


################################################################################
# Main
################################################################################


def main(argv):
    """
    Handles configuration and user database parsing and writing, and calls
    chosen program function.
    """
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
    config = gutil.parse_config(config_file)
    # get the list of notebook users
    (users, csv_dialect) = gutil.read_database(config["user list"])
    try:
        # call appropriate function
        if argv[0].lower() == "setup":
            setup(config, users)
        elif argv[0].lower() == "send":
            send(config, users)
        elif argv[0].lower() == "launch":
            launch(config, users)
        elif argv[0].lower() == "shutdown":
            shutdown(config, users)
        elif argv[0].lower() == "retrieve":
            retrieve(config, users)
        elif argv[0].lower() == "remove":
            remove(config, users)
        else:
            raise ValueError(u"unrecognised option: '{0}'".format(argv[0]))
    except BaseException as err:
        LOGGER.debug(u"pssst:", exc_info=True)
        raise err
    finally:
        # write user information
        gutil.write_database(config["user list"], users, csv_dialect)


def main_command():
    LOGGER.setLevel(logging.INFO)
#    LOGGER.setLevel(logging.DEBUG)
    LOGGER.addHandler(logging.StreamHandler())
    argc = len(sys.argv)
    if argc < 2 or argc > 3:
        LOGGER.critical(u"Usage:\nsudo python {0} <setup | send | launch |"\
                u" shutdown | retrieve | remove>"\
                u" [config file: path]".format(sys.argv[0]))
        sys.exit(2)
    rec = 0
    try:
        main(sys.argv[1:])
    except Exception as err:
        rec = err.errno if hasattr(err, "errno") else 1
        LOGGER.critical(str(err))
    finally:
        # perform clean-up
        logging.shutdown()
    sys.exit(rec)

