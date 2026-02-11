# Verilator image, only used to copy some binaries out of it (see below).
ARG VERILATOR_VERSION=5.044
FROM verilator/verilator:v${VERILATOR_VERSION} AS verilator

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

# Install Verilator from official Verilator container image.
COPY --from=verilator /usr/local/share/verilator /usr/local/share/verilator
COPY --from=verilator /usr/local/bin/verilator* /usr/local/bin/
COPY --from=verilator /usr/local/share/man /usr/local/share/man
COPY --from=verilator /usr/local/share/pkgconfig/verilator.pc /usr/local/share/pkgconfig

# Install NVC from an upstream Debian package.
# (Use apt instead of dpkg to resolve dependencies automatically.)
ARG NVC_VERSION=1.18.2
ARG NVC_SHA256=bb6f19a84a398e13c56649996262db63ed9787e19dd0ad894774e132e170b785
RUN mkdir -p /tmp/nvc-install \
    && curl -SLo /tmp/nvc-install/nvc.deb "https://github.com/nickg/nvc/releases/download/r${NVC_VERSION}/nvc_${NVC_VERSION}-1_amd64_ubuntu-24.04.deb" \
    && echo "${NVC_SHA256} /tmp/nvc-install/nvc.deb" | sha256sum --check \
    && apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt -y install --no-install-recommends /tmp/nvc-install/nvc.deb \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/nvc-install
