#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
========================
Return IPython Directory
========================

:Author:
    Moritz Emanuel Beber
:Date:
    2012-01-17
:Copyright:
    Copyright(c) 2012 Jacobs University of Bremen. All rights reserved.
:File:
    notebooks.py
"""


from IPython.utils.path import get_ipython_dir


if __name__ == "__main__":
    print(get_ipython_dir())

