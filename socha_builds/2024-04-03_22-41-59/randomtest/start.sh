#!/bin/sh

# Exit immediately if any command fails
set -e

# Sets the environment variable, which specifies the location for pip to store its cache files
export XDG_CACHE_HOME=./randomtest/.pip_cache

# Sets the environment variable, which adds the directory to the list of paths that Python searches for modules and packages when they are imported.
export PYTHONPATH=./randomtest/packages:$PYTHONPATH

# Install the package socha and dependencies
pip install --no-index --find-links=./randomtest/dependencies/ --target=./randomtest/packages/ --cache-dir=./randomtest/.pip_cache ./randomtest/dependencies/networkx-3.2.1-py3-none-any.whl ./randomtest/dependencies/setuptools-69.2.0-py3-none-any.whl ./randomtest/dependencies/socha-2.2.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl ./randomtest/dependencies/xsdata-22.9-py3-none-any.whl 

# Run the randomLogic.py script with start arguments
python3 ./randomtest/randomLogic.py "$@"
