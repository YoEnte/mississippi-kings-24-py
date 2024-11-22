#!/bin/sh

# Exit immediately if any command fails
set -e

# Sets the environment variable, which specifies the location for pip to store its cache files
export XDG_CACHE_HOME=./slowspeed_1.0.3/.pip_cache

# Sets the environment variable, which adds the directory to the list of paths that Python searches for modules and packages when they are imported.
export PYTHONPATH=./slowspeed_1.0.3/packages:$PYTHONPATH

# Install the package socha and dependencies
pip install --no-index --find-links=./slowspeed_1.0.3/dependencies/ --target=./slowspeed_1.0.3/packages/ --cache-dir=./slowspeed_1.0.3/.pip_cache ./slowspeed_1.0.3/dependencies/networkx-3.2.1-py3-none-any.whl ./slowspeed_1.0.3/dependencies/setuptools-69.2.0-py3-none-any.whl ./slowspeed_1.0.3/dependencies/socha-2.2.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl ./slowspeed_1.0.3/dependencies/xsdata-22.9-py3-none-any.whl 

# Run the logic.py script with start arguments
python3 ./slowspeed_1.0.3/logic.py "$@"
