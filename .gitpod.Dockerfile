FROM gitpod/workspace-full-vnc

USER gitpod

## Install Python with --enable-shared
ARG PYTHON_VERSION=3.8.2
RUN rm -rf ${HOME}/.pyenv/versions/${PYTHON_VERSION}
RUN PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install ${PYTHON_VERSION}
RUN pyenv global ${PYTHON_VERSION}

RUN pip3 install --upgrade pip

# Install linters
RUN pip3 install -U flake8 pylint

# Re-synchronize the package index
RUN sudo apt-get update

# Install needed packages
RUN sudo apt-get install -y flex gnat gtkwave swig
RUN sudo rm -rf /var/lib/apt/lists/*

## Install Icarus Verilog
RUN brew install icarus-verilog

## Install Verilator
RUN brew install verilator

## Install GHDL
ENV GHDL_BRANCH=v0.37
RUN git clone https://github.com/ghdl/ghdl.git --depth=1 --branch ${GHDL_BRANCH} ghdl \
    && cd ghdl \
    && ./configure \
    && make -s \
    && sudo make -s install \
    && cd .. \
    && rm -rf ghdl

# Install cvc
RUN git clone https://github.com/cambridgehackers/open-src-cvc.git --depth=1 cvc \
    && cd cvc/src \
    && make -f makefile.cvc64 -s \
    && sudo cp cvc64 /usr/local/bin \
    && cd ../.. \
    && rm -rf cvc
