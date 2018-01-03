FROM librecores/ci-osstools:2018.1-rc1

# make sources available in docker image
RUN mkdir -p /src
ADD . /src
WORKDIR /src

RUN apt-get update; apt-get install -y virtualenv python3-venv python3-dev

# Build and test using Python 2
RUN mkdir /build-py2; cp -r /src /build-py2
ENV COCOTB=/build-py2/src
RUN bash -lc 'virtualenv /build-py2/venv; source /build-py2/venv/bin/activate; pip install coverage xunitparser; make -C /build-py2/src test'

# Build and test using Python 3
RUN mkdir /build-py3; cp -r /src /build-py3
ENV COCOTB=/build-py3/src
RUN bash -lce 'python3 -m venv /build-py3/venv; source /build-py3/venv/bin/activate; pip install coverage xunitparser; make -C /build-py3/src test'

