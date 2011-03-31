# vcs.hc's setup.py
from distutils.core import setup

import os, sys
long_description = open(os.path.join(os.path.dirname(sys.argv[0]), 'README.txt')).read()

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
    long_description = long_description
)
