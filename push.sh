#!/bin/bash

TARGET_URL=${1:-cherrybum:/var/www/html/downloads/}

#--------------------------------------------------
REL_DIR=$(dirname $0)
cd $REL_DIR

# Quick validation(s)
[ ! -f setup.py ] && { echo "Where is \"setup.py\"?. Exiting."; exit 1; }

# Dynamic variables
NAME=$(python setup.py --name)
VER=$(python setup.py --version)
TARBALL=dist/${NAME}-${VER}.tar.gz

# Build the source package
python setup.py sdist

# Ensure permissions and push
chmod 644 $TARBALL
scp -p $TARBALL $TARGET_URL
