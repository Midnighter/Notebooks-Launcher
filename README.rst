===============================
IPython Notebook Infrastructure
===============================


Outline
-------

The purpose of this repository is to facilitate setting up separate IPython
notebook kernels for a list of users on one host machine.

Usage
-----

There are four different ways to invoke the `notebooks.py` script and it always
requires **superuser privileges** in order to run properly. Additionally, an
alternative configuration file may be supplied as an argument.::

    notebooks.py <setup | launch | shutdown | remove> [config file]

* Each invocation requires the file with the user database to be present. The
  order of the header line does not matter. Running `setup` requires only the
  username to be present (later email may be used to send login information to
  users directly).

* `setup` will parse the user database and genereate system accounts for them.
  Passwords for the system and to protect the ipython notebook are generated. If
  the IPython profile specified in the `config file` exists for the local user,
  the `*.py` files and the `startup/*.py` files are copied to the other users. It
  will also use a predefined directory and copy the material therein into each
  users' account. **Run the setup only once, since copying of files will be
  done without mercy for existing files!**

* `launch` assigns a unique port to each user in a dumb way. It does not check
  whether the port is in use. IPython may check it but the change in port is not
  recognised. At the end a webserver will be launched that should direct each
  user to their specific notebook instance. The Python process will continue to
  run until terminated which shuts down the webserver.

* `shutdown` kills all IPython notebook kernels running under the user
  names provided, so be careful! Additionally, it will copy the user generated
  files in the specified tutorial directory back into the owner's storage area
  for evaluation.

* `remove` will delete all user accounts including their home directories, be
  absolutely sure you want to do this.

* A sample students.csv and notebooks.cfg file are provided.

Notes
-----

* The notebook kernel instances require an ssl certificate file. This file must be
  in a location and have permissions that allow every user on the system to access
  it (each user is added to a supplementary group which could also be used for
  this but that's not tested).

* On the hosting machine your firewall needs to allow tcp ports in the range
  of <webserver port> to <webserver port + number of students>.

Requirements
------------

* A running installation of the IPython notebook (http://ipython.org/) which
  will also require `tornado` and `pexpect`.

