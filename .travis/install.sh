#!/bin/bash
set -e

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    # Manually install Python
    brew outdated pyenv || brew upgrade pyenv
    # virtualenv doesn't work without pyenv knowledge. venv in Python 3.3
    # doesn't provide Pip by default. So, use `pyenv-virtualenv <https://github.com/yyuu/pyenv-virtualenv/blob/master/README.md>`_.
    brew install pyenv-virtualenv
    pyenv install $PYTHON
    # I would expect something like ``pyenv init; pyenv local $PYTHON`` or
    # ``pyenv shell $PYTHON`` would work, but ``pyenv init`` doesn't seem to
    # modify the Bash environment. ??? So, I hand-set the variables instead.
    export PYENV_VERSION=$PYTHON
    export PATH="/Users/travis/.pyenv/shims:${PATH}"
    pyenv virtualenv venv
    source venv/bin/activate
    # A manual check that the correct version of Python is running.
    python --version

    # icarus Verilog
    brew install icarus-verilog

    pip install tox-travis flake8
elif [[ $TRAVIS_OS_NAME == 'linux' ]]; then
    sudo apt-get -qq update
    sudo apt-get -qq install -y --no-install-recommends git gperf make autoconf g++ flex bison
    mkdir -p /tmp/iverilog
    cd /tmp/iverilog
    git clone https://github.com/steveicarus/iverilog.git --depth=1 --branch v${ICARUS_VERILOG_VERSION} .
    sh autoconf.sh
    ./configure
    make -s -j${MAKE_JOBS}
    sudo make -s install

    pip install tox-travis flake8
else
    echo Unknown OS $TRAVIS_OS_NAME, nothing to install! >&2
fi
