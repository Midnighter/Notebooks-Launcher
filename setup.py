#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
=================================
IPython Notebook Launcher Package
=================================

:Authors:
    Moritz Emanuel Beber
:Date:
    2012-10-30
:Copyright:
    Copyright(c) 2012 Jacobs University of Bremen. All rights reserved.
:File:
    setup.py
"""


#from distutils.core import setup
from setuptools import setup


setup(
    name = "nblauncher",
    version = "0.2",
    description = "account management for multiple ipython notebook users",
    author = "Moritz Emanuel Beber",
    author_email = "moritz (dot) beber (at) gmail (dot) com",
    url = "https://github.com/Midnighter/Notebooks-Launcher",
    packages = ["nblauncher"],
    entry_points = {"console_scripts": ["nblauncher = nblauncher.notebooks:main_command"]}
    )

