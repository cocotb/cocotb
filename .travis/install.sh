#!/bin/bash
#
# Install build and test dependencies for cocotb in Travis
#
# This script is *sourced* before the build and test in Travis is started.
# The script has two goals:
#
# - Install Python where Travis doesn't provide it itself.
# - Install Icarus Verilog
# - Install flake8, pytest and tox
#
# For tox we use a wrapper called tox-travis which detects the targeted Python
# version in this particular build and sets up tox correctly to run only for
# this Python version. Multiple Python versions are tested in multiple build
# jobs.
#

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    # Install Python
    # TRAVIS_PYTHON_VERSION is the environment variable typically set by Travis
    # itself when using its Python language support. This support is not
    # available for osx. We hence manually install Python using pyenv.
    # The used pyenv helper script expects the Python version in PYENV_VERSION,
    # while tox-travis expects it in TRAVIS_PYTHON_VERSION; hence both variables
    # are needed.
    export PYENV_VERSION=$TRAVIS_PYTHON_VERSION
    wget -q https://github.com/praekeltfoundation/travis-pyenv/releases/download/0.4.0/setup-pyenv.sh
    source setup-pyenv.sh

    # Install Icarus Verilog
    brew install icarus-verilog || exit 1

    # Install all other Python build/test dependencies
    pip install tox-travis pytest flake8 || exit 1

    # Check installation
    pytest --version
    flake8 --version
    iverilog -V 2>&1 | head -n1

elif [[ $TRAVIS_OS_NAME == 'linux' ]]; then
    # Install Icarus Verilog
    sudo apt-get -qq update
    sudo apt-get -qq install -y --no-install-recommends git gperf make autoconf g++ flex bison
    mkdir -p /tmp/iverilog
    cd /tmp/iverilog;
    git clone https://github.com/steveicarus/iverilog.git --depth=1 --branch v${LINUX_ICARUS_VERILOG_VERSION} .
    sh autoconf.sh || exit 1
    ./configure || exit 1
    make -s -j2 || exit 1
    sudo make -s install || exit 1

    # Install all other Python build/test dependencies
    pip install tox-travis pytest flake8 || exit 1

    # Check installation
    pytest --version
    flake8 --version
    iverilog -V 2>&1 | head -n1
else
    echo Unknown OS $TRAVIS_OS_NAME, nothing to install! >&2
fi

# Ensure that whatever the install.sh script does we're back in our build dir
cd $TRAVIS_BUILD_DIR
