==========================
IPython Notebooks Launcher
==========================


Outline
-------

The purpose of this repository is to facilitate setting up separate IPython
notebook kernels for a list of users on one host machine.

Compatibility
-------------

*Should* work for:

* most Linux flavours
* Mac OS (tested on 10.8)

Tests
-----

Currently, the test script fails a number of tests on Mac but everything works
smoothly when the exact same sequence of commands is run interactively. Also,
running the test cases still manages to add and remove the users and groups.

Installation
------------

A setup script is provided::

    [sudo] python setup.py install

This will install the nblauncher package as well as two executables `nblauncher`
and `ipython_dir`. The latter is necessary for the `nblauncher` to find the
location of the IPython Home for all users.

Usage
-----

Once installed, the program `nblauncher` becomes available which can be invoked
in six different ways. It always requires **superuser privileges** in order to
run properly. Additionally, an alternative configuration file may be supplied
as an argument.::

    sudo nblauncher <setup | send | launch | shutdown | remove | retrieve> [config file]

* Each invocation requires the file with the user database to be present. The
  order of the header line does not matter. Running `setup` requires only the
  username to be present (in future email may be used to send login information
  to users directly).

* **setup** will generate system accounts for the users.
  Passwords for the system and to protect the ipython notebook are generated. If
  the IPython profile specified in the `config file` exists for the local user,
  the `*.py` files and the `startup/*.py` files are copied to the other users.
  It also internally invokes **send**.

* **send** will use a predefined directory and copy the material therein into each
  users' account.

* **launch** assigns a unique port to each user in a dumb way. It does not check
  whether the port is in use. IPython may check it but the change in port is not
  recognised. At the end a webserver will be launched that should direct each
  user to their specific notebook instance. The Python process will continue to
  run until terminated which shuts down the webserver.

* **shutdown** kills all IPython notebook kernels running under the user
  names provided, so be careful!

* **remove** will **delete all user accounts including their home directories**, be
  absolutely sure you want to do this! It will call **retrieve** internally
  before deleting the user.

* **retrieve** will copy the user generated files in the specified tutorial
  directory back into the owner's storage area for evaluation.

* Sample students.csv and notebooks.cfg files are provided.

Notes
-----

* The notebook kernel instances require an `ssl certificate`_ file. This file must be
  in a location and have permissions that allow every user on the system to access
  it (each user is added to a supplementary group which could also be used for
  this but that's not tested). This means that the gid or `others` must have
  read and execute permissions for the certificate file and the **whole
  directory tree** leading to the file. Usually this is done by invoking::
    chmod o+rx mycert.pem
  on the file and directories.

* On the hosting machine your firewall needs to allow tcp ports in the range
  of <webserver port> to <webserver port + number of students>.

Requirements
------------

* A running installation of the `IPython Notebook`_ which will also require
  `tornado` and `pexpect`.

.. _`IPython Notebook`: http://ipython.org/ipython-doc/stable/install/install.html#installnotebook
.. _`ssl certificate`: http://ipython.org/ipython-doc/stable/interactive/htmlnotebook.html#security

