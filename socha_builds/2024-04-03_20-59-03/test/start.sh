#!/bin/sh

# Exit immediately if any command fails
set -e

# Sets the environment variable, which specifies the location for pip to store its cache files
export XDG_CACHE_HOME=./test/.pip_cache

# Sets the environment variable, which adds the directory to the list of paths that Python searches for modules and packages when they are imported.
export PYTHONPATH=./test/packages:$PYTHONPATH

# Install the package socha and dependencies
pip install --no-index --find-links=./test/dependencies/ --target=./test/packages/ --cache-dir=./test/.pip_cache ./test/dependencies/networkx-3.2.1-py3-none-any.whl ./test/dependencies/setuptools-69.2.0-py3-none-any.whl ./test/dependencies/socha-2.2.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl ./test/dependencies/xsdata-22.9-py3-none-any.whl 

# Run the logic.py script with start arguments
python3 ./test/logic.py "$@"
