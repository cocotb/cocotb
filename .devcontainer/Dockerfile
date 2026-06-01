ARG VERILATOR_VERSION=5.048
ARG UV_VERSION=0.11.16

# Container images used only to copy binaries out of it (see below).
FROM verilator/verilator:v${VERILATOR_VERSION} AS verilator
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# See https://github.com/devcontainers/images/tree/main/src/base-ubuntu/history
# for a description of what's in this base image.
FROM mcr.microsoft.com/devcontainers/base:2-ubuntu-24.04

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        bear \
        bison  \
        build-essential \
        ccache \
        clang \
        clangd \
        colordiff \
        doxygen \
        flex \
        gdb \
        gdb \
        gh \
        ghdl \
        git \
        git-absorb \
        gperf  \
        graphviz \
        iverilog \
        libenchant-2-dev \
        lldb \
        pre-commit \
        python3-dev \
        python3-pip \
        python3-venv \
        valgrind \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install UV from the official uv container image.
COPY --from=uv /uv /uvx /usr/local/bin/

# In a Dev Container, the venv tends to be in the git repository, which is
# mounted from the host and hence a different mount than the cache directory.
# Avoid the warning about uv being unable to use hardlinks in such an
# environment.
ENV UV_LINK_MODE=copy

# Install Verilator from official Verilator container image.
COPY --from=verilator /usr/local/share/verilator /usr/local/share/verilator
COPY --from=verilator /usr/local/bin/verilator* /usr/local/bin/
COPY --from=verilator /usr/local/share/man /usr/local/share/man
COPY --from=verilator /usr/local/share/pkgconfig/verilator.pc /usr/local/share/pkgconfig

# Install NVC from an upstream Debian package.
# (Use apt instead of dpkg to resolve dependencies automatically.)
ARG NVC_VERSION=1.21.0
ARG NVC_SHA256=d2fc583c0b51b4784886b5180ed7edad3e02f8351add85286c080bfee7a9786d
RUN mkdir -p /tmp/nvc-install \
    && curl -SLo /tmp/nvc-install/nvc.deb "https://github.com/nickg/nvc/releases/download/r${NVC_VERSION}/nvc_${NVC_VERSION}-1_amd64_ubuntu-24.04.deb" \
    && echo "${NVC_SHA256} /tmp/nvc-install/nvc.deb" | sha256sum --check \
    && apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt -y install --no-install-recommends /tmp/nvc-install/nvc.deb \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/nvc-install
