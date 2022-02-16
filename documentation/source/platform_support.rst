.. _platform-support:

****************
Platform Support
****************

cocotb supports Windows, Linux, and macOS, with a wide range of Python versions.
This page describes which platform combinations we test and support.

The :ref:`platform-support-policy` discusses the underlying policy.

.. note::

  In many cases cocotb will work on platforms not listed on this page, and we aim to fix compatibility issues as we become aware of them.
  However, we encourage less experienced users to stick with one of the supported options for a good user experience.

  Please reach out to the cocotb team if you would like to see support for a different platform, and are willing to contribute to maintaining it.

Supported Python Versions
=========================

The following versions of Python (CPython), and all associated patch releases (e.g. 3.8.4), are supported by cocotb.

* Python 3.6
* Python 3.7
* Python 3.8
* Python 3.9
* Python 3.10

Supported Linux Distributions and Versions
==========================================

Linux users are in the privileged position of being able to choose from huge variety of distributions.
While most of them are compatible with each other, some subtle differences exist.
Even though cocotb aims to be agnostic to the distribution, and generally works well on most of them, we are explicitly supporting and testing on a limited subset of distributions which are common in EDA environments.

We encourage especially users less experienced with Linux to use one of the supported and tested distributions listed below to ensure a smooth cocotb experience.

Linux distributions typically ship a default version of Python called "system Python".
This version of Python can be used with cocotb unless noted otherwise.

* **Red Hat Enterprise Linux (RHEL) 7.7+ amd64**,
  shipping with Python 3.6, pip 9, and glibc 2.17.
  `Upstream support until June 2024 <https://access.redhat.com/support/policy/updates/errata#Life_Cycle_Dates>`_.
* **Red Hat Enterprise Linux (RHEL) 8 amd64**,
  shipping with Python 3.6, pip 9, and glibc 2.28.
  `Upstream support until May 2029 <https://access.redhat.com/support/policy/updates/errata#Life_Cycle_Dates>`_.
* **Ubuntu 18.04 LTS amd64**,
  shipping with Python 3.6, pip 9, and glibc 2.27.
  `Upstream support until April 2023 <https://wiki.ubuntu.com/Releases>`_.
* **Ubuntu 20.04 LTS amd64**, shipping with Python 3.8, pip 20, glibc 2.31.
  `Upstream support until April 2025 <https://wiki.ubuntu.com/Releases>`_.

.. note::

  * Binary-compatible RHEL-clones, such as CentOS, are equally supported.
  * For RHEL only Red Hat-supported minor versions are supported by cocotb.
  * Compatible Ubuntu derivatives, such as Kubuntu, Xubuntu, etc., are equally supported.

Supported Windows Versions
==========================

* **Windows 10 x86_64**
* **Windows 11 x86_64**


Supported macOS Versions
========================

* **macOS 10.15 (Catalina)**
* **macOS 11 (Big Sur)**

.. _platform-support-policy:

cocotb Platform Support Policy
==============================

cocotb's platform support policy is driven by two main considerations.

1. Support cocotb on the platforms our users are using.
2. Allow our users to use the latest cocotb release.

The first item is obvious, but comes with interesting implications:
for hardware projects it is common to use "mature" platforms such as the previous version of RHEL, and stay on that for the duration of a chip project, which might last multiple years.
For cocotb, this means supporting rather old Python and operating system versions.

The second item is less obvious.
One might argue that users of older Python or operating system versions should simply use an old version of cocotb.
There are two reasons against applying this rule too agressively.
First of all, we want to give users the benefit of using the latest and greatest version of cocotb on the platform they are on (and are typically unable to change).
But even more importantly, every user who is on the latest release is beneficial for the cocotb project.
Supporting multiple older cocotb releases comes a cost: users report bugs which have been fixed in later releases, patch releases need to be supplied (e.g. for security problems), and integrating improvements our users made becomes harder.

When determining the list of supported operating systems and Python versions we are trying to balance those two main considerations.
The guidance below adds a bit more color to the policy we apply for choosing supported Python and operating system versions.

Python Support
--------------

cocotb aims to support a wide range of Python versions as long as they are supported either by the upstream Python project, or by another entity.

In general, cocotb aims to support all versions of Python `supported by the Python upstream community <https://devguide.python.org/#status-of-python-branches>`_ at the time a cocotb release was made.
Additionally, the Python version a supported Linux distribution ships with (system Python) is typically supported as well,
as long as it receives updates by the operating system vendor (e.g. Red Hat, Debian, or Canonical).

Only the standard CPython implementation is supported, the alternatives are not supported.

Operating System Support
------------------------

cocotb aims to support all operating systems commonly used by our users.
As such, we try to match the support matrix of major EDA tools to enable a seamless interaction between simulators and cocotb.
Additionally, cocotb should work on the latest version of Windows, Linux, and macOS to ensure users can update their operating system freely without being blocked by cocotb.

cocotb only supports x86_64 architectures and requires a 64-bit operating system.
(Note: 32-bit x86 applications can be run on 64-bit operating systems.)
