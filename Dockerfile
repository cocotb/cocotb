FROM ubuntu:16.04

# travis-ci only provides 2
ARG MAKE_JOBS=-j2

# Simulation 
ARG ICARUS_VERILOG_VERSION=10_2 

RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
       wget \
       git \
       gperf \
       make \
       autoconf \
       g++ \
       flex \
       bison \
       python2.7-dev python3-dev\
       python-pip \
       python3 \
       virtualenv \
       python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && pip install --upgrade pip \
    && g++ --version

# Icarus Verilog 
ENV ICARUS_VERILOG_VERSION=${ICARUS_VERILOG_VERSION} 
WORKDIR /usr/src/iverilog
RUN git clone https://github.com/steveicarus/iverilog.git --depth=1 --branch v${ICARUS_VERILOG_VERSION} . \
    && sh autoconf.sh \
    && ./configure \
    && make -s ${MAKE_JOBS} \
    && make -s install \
    && rm -r /usr/src/iverilog


# make sources available in docker image - one copy per python version
COPY . /build-py2/src
COPY . /build-py3/src

# Build and prepare using Python 2
RUN bash -c 'virtualenv /build-py2/venv; source /build-py2/venv/bin/activate; pip install coverage xunitparser; deactivate'

# Build and prepare virtual env using Python 3
RUN bash -c 'python3 -m venv /build-py3/venv; source /build-py3/venv/bin/activate; pip install coverage xunitparser; deactivate'


