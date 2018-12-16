#!/bin/bash
set -e
set -x

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    # Install Python
    wget -q https://github.com/praekeltfoundation/travis-pyenv/releases/download/0.4.0/setup-pyenv.sh
    source setup-pyenv.sh

    # Install Icarus Verilog
    brew install icarus-verilog

    # Install all other Python build/test dependencies
    pip install tox-travis flake8 pytest

    # Check installation
    pytest --version
    flake8 --version
elif [[ $TRAVIS_OS_NAME == 'linux' ]]; then
    # Install Icarus Verilog
    sudo apt-get -qq update
    sudo apt-get -qq install -y --no-install-recommends git gperf make autoconf g++ flex bison

    mkdir -p /tmp/iverilog
    cd /tmp/iverilog;
    git clone https://github.com/steveicarus/iverilog.git --depth=1 --branch v${ICARUS_VERILOG_VERSION} .
    sh autoconf.sh
    ./configure
    make -s -j${MAKE_JOBS}
    sudo make -s install

    # Install all other Python build/test dependencies
    pip install tox-travis flake8 pytest

    # Check installation
    pytest --version
    flake8 --version
else
    echo Unknown OS $TRAVIS_OS_NAME, nothing to install! >&2
fi

