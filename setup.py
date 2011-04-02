# vcs.hc's setup.py

try:
    from setuptools import setup, find_packages
except ImportError:
    print "If you want to use setuptools's setup(), install setuptools first."
    from distutils.core import setup

import os
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "hcvcs",
    version = "1.0.0",
    description = "VERITAS Cluster Server Health Check",
    author = "Jon Miller",
    author_email = "jonEbird@gmail.com",
    url = "https://github.com/jonEbird/hc-vcs",
    download_url = "http://jonebird.com/downloads/hcvcs-1.0.0.tgz",
    keywords = ["veritas", "VCS", "cluster"],
    classifiers = [
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: POSIX",
        "Topic :: System :: Clustering",
        ],
    py_modules = ['hcvcs'],
    #packages = ['packagename'],
    scripts = ['hc-vcs.py'],
    install_requires = ["paramiko"],
    long_description = read('README'),
)
