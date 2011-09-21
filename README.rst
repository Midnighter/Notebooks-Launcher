===============================
IPython Notebook Infrastructure
===============================


Outline
-------

The purpose of this repository is to facilitate setting up separate IPython
notebook kernels for a list of users on one host machine.

Usage
-----

There are three scripts and some configuration files provided. All three scripts
require superuser privileges.::

    setup_notebooks.py

    launch_notebooks.py

    shutdown_notebooks.py

* The setup script will parse a file containing user names and their e-mail
  addresses. It will generate system user names from the e-mail addresses and set up
  user accounts on the system. Additionally, it can copy some material into the
  user directories.

* The launch script starts an IPython notebook with user privileges in their
  material directory, so that they should have direct access to the provided
  material.

* The shutdown script kills all IPython notebook kernels running under the user
  names provided, so be careful!

* A sample students.csv and notebooks.cfg file are provided.

Requirements
------------

* A running installation of the IPython notebook (http://ipython.org/)
* probably the code will only work for Python >= 2.6

