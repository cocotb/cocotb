# Cocotb Contribution Guidelines

Welcome to the cocotb development!
We are an inclusive community with the common goal of improving the cocotb, a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.
This guide explains how to contribute to cocotb, and documents the processes we agreed on to manage the project.
All processes in this document are designed to streamline the development effort, to avoid bottlenecks, and to ultimately give a pleasant experience to all involved.


## Setting Up a Development Environment

Assuming you have used cocotb prior to reading this guide, you will already have the cocotb [installation prerequisites](https://docs.cocotb.org/en/latest/install.html) and standard development tools (editor, shell, git, etc.) installed.

Additionally, you will need [doxygen](https://www.doxygen.nl/index.html), for building documentation, and [tox](https://pypi.org/project/tox/), for building documentation and running regression tests.

We recommend if you are using a Linux distribution to use your system package manager to install doxygen.
Likewise, doxygen can be installed using the homebrew package manager on Mac OS.
Windows contributors should download a binary distribution installer from the main website.

`tox` is a Python project and can be installed with `pip`.

```command
pip install tox
```

Finally, you must download the cocotb source from Github if you have not already done so.

```command
git clone https://github.com/cocotb/cocotb
```

Now you are ready to contribute!


## Running Tests Locally

First, [set up your development environment](#setting-up-a-development-environment).

Our tests are managed by `tox`, which runs both `pytest` tests and our system of makefiles.
The regression does not end on the first failure, but continues until all tests in the `test` and `example` directories have been run.

To run the tests locally with `tox`, you will need to select an appropriate test environment.
Valid test environments are formatted as `{your python version}-{your OS}`.
Valid python version values are `py35`, `py36`, `py37`, `py38`, or `py39`;
and valid OS values are `linux`, `macos`, or `windows`.
For example, a valid test environment is `py38-linux`.
You can see the list of valid test environments by running the below command.

```command
tox -l
```

Once you know the test environment you wish to use, call `tox` .

```command
tox -e py38-linux
```

At the end of the regression, if there were any test failures, the tests that failed will be printed.
Otherwise, tox will print a green `:)`.

### Selecting a Regression Language and Simulator

`tox` supports the usage of the environment variables `SIM` and `TOPLEVEL_LANG` to select a simulator and language to run the regression.
By default the tests will attempt to run with the Icarus Verilog simulator.
For example, if you wanted to run tests with GHDL on Linux with Python 3.8, you would issue the following command.

```command
SIM=ghdl TOPLEVEL_LANG=vhdl tox -e py38-linux
```

### Running Individual Tests Locally

Each test under `/tests/test_cases/*/` and `/examples/tests/` can be run individually.
This is particularly useful if you want to run a particular test that fails the regression.

First you must install cocotb from source by navigating to the project root and issuing the following.

```command
python -m pip install .
```

On Windows, you must install cocotb from source like so.

```command
python -m pip install --global-option build_ext --global-option --compiler=mingw32 .
```

Once that has been done, you can navigate to the directory containing the test you wish to run.
Then you may issue an [appropriate](https://docs.cocotb.org/en/stable/quickstart.html#running-your-first-example) `make` command.

```command
make SIM=icarus
```


## Building Documentation Locally

First, [set up your development environment](#setting-up-a-development-environment).

Documentation is built locally using `tox`.
The last message in the output will contain a URL to the documentation you just built.
Simply copy and paste the link into your browser to view it.
The documentation will be built in the same location on your hard drive on every run, so you only have to refresh the page to see new changes.

To build the documentation locally on Linux or Mac, issue the following command.

```command
tox -e docs
```

Building the documentation is not currently supported on Windows.


## Architecture and Scope of Cocotb

Cocotb has seen adoption in a wide variety of scenarios with sometimes conflicting requirements.
To foster experimentation and to decentralize the development process the architecture of cocotb is highly modular.
A solid core forms the foundation upon which extensions can provide higher-level functionality.

The core of cocotb are
- the infrastructure to write testbenches with coroutines, threads, etc.,
- the abstraction and interaction with simulators through interfaces like VPI, GPI, etc.,
- tooling to run tests, and
- core primitives to interact with the simulation: triggers, data access classes, etc.

As a general rule, functionality beyond this core set should go into extensions.
However, none of these rules are set in stone.
They can and should be challenged at times to ensure the project stays relevant to the majority of its users.


## How to Get Changes Merged

Have you fixed a bug in cocotb, or want to add new functionality to it?
Cocotb follows the typical [GitHub flow](https://guides.github.com/introduction/flow/) and makes use of pull requests and reviews.
Follow the steps below to get your changes merged, i.e. integrated into the main cocotb codebase.

1. Create an issue ticket on [cocotb's GitHub issue tracker](https://github.com/cocotb/cocotb/issues) describing the problem.
   Issues are also a good place to discuss design options with others before writing code.
2. [Fork](https://help.github.com/articles/fork-a-repo/) the [cocotb GitHub repository](https://github.com/cocotb/cocotb) into your personal namespace.
3. Create a new branch off the `master` branch for your set of changes.
   Use one branch per "topic," i.e. per set of changes which belong together.
4. Create one or multiple commits to address the issue.
   Make sure to read and follow the [Patch Requirements](#patch-requirements) when preparing your commits.
5. Create new [pull request (PR)](https://github.com/cocotb/cocotb/pulls).
6. When you submit (or update) the pull request, a suite of regression tests will run.
   If any of them turns "red," i.e. reports a failure, you most likely need to fix your code before it can be merged.
7. The pull request needs to be reviewed by at least one maintainer.
   We aim to give feedback to all pull requests within a week, but as so often, life can get in the way.
   If you receive no feedback from a maintainer within that time, please contact them directly (e.g. on [Gitter](https://gitter.im/cocotb) or email).
   You can find a [list of all maintainers](#maintainers) below.
   If a maintainer asks you to explain or modify code, try to do so.
8. Once your code has at least one positive review from a maintainer and no maintainer strongly objects it your code is ready to be merged into the `master` branch.


## Patch Requirements

All changes which should go into the main codebase of cocotb must follow this set of requirements.

- The code must be within the [scope of cocotb](#architecture-and-scope-of-cocotb).
- All code must be licensed under the [Revised BSD License](https://github.com/cocotb/cocotb/blob/master/LICENSE).
  By contributing to this project you signal your agreement with these license terms.
- All code must follow the established coding standards.
  For Python code, follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.
- All code must pass existing tests.
  New functionality must be accompanied by tests, and bug fixes should add tests to increase the test coverage and prevent regressions.
- If code changes or enhances documented behavior the documentation should be updated.
- If a change is user-visible, a newsfragment should be added to `documentation/source/newsfragments`.
- All pull requests must be accepted by at least one maintainer, with no maintainer strongly objecting.
  Reviews must be performed by a person other than the primary author of the code.
- All commits should follow established best practices when creating a commit message:
   - The first line of the commit message is the short summary of what the code change does.
     Keep this line below 50 characters.
   - Then have one blank line.
   - Now comes the long description of the commit.
     Use this text to discuss things which are not obvious from the code, especially *why* changes were made.
     Include the GitHub issue number (if one exists) in the form "Fixes #nnn" ([read more about that](https://help.github.com/articles/closing-issues-using-keywords/)).
     Keep each description line below 72 characters.
- Use the following header for new non-example files:
  ```python
  # Copyright cocotb contributors
  # Licensed under the Revised BSD License, see LICENSE for details.
  # SPDX-License-Identifier: BSD-3-Clause
  ```
- Use the following header for new example files:
  ```python
  # This file is public domain, it can be freely copied without restrictions.
  # SPDX-License-Identifier: CC0-1.0
  ```

## Managing of Issues and Pull Requests

The cocotb project makes use of GitHub labels attached to issues and pull requests to structure the development process.
Each issue and pull request can have multiple labels assigned.

The `type` labels define the type of issue or PR:
- `type:bug`: a bug in existing functionality
- `type:feature`: new functionality
- `type:question`: a support question
- `type:cleanup`: cleanup or refactoring on code, documentation, or other areas
- `type:deprecation`: API that should warn and eventually be removed

The `status` labels give a quick impression of the current status of the issue or PR:
- `status:worksforme`: the issue it not reproducible, or intended behavior (i.e. not a bug)
- `status:blocked`: further progress is blocked by a dependency, e.g. other code which must be commited first.
- `status:needs-info`: feedback from someone is required. The issue/PR text gives more details.
- `status:duplicate`: the same issue is already being handled in another issue/PR.
- `status:close?`: issues which can probably be closed, but need a second pair of eyes
- `status:needs-proprietary-testing`: Help needed testing on a proprietary tool
- `status:out-of-scope`: An issue or PR that was closed because the feature or bug was deemed to be out of scope

For the use in pull requests the following additional status labels are defined:
- `status:needs-review`: this PR needs at least one review
- `status:changes-requested`: changes are requested to the code
- `status:ready-for-merge`: this PR is ready (according to the [Patch Requirements](#patch-requirements)) to be merged
- `status:needs-rebase`: needs a git rebase
- `status:needs-newsfragment`: Needs a towncrier newsfragment for the changelog

The `category` labels help maintainers to filter issues which are relevant to their area of expertise:
- `category:OS:MacOS`: Mac OS/OS X specific issues
- `category:OS:Linux`: Linux specific issues
- `category:OS:Windows`: Microsoft Windows-specific issues
- `category:simulators`: simulator support, including VPI/GPI/etc.
- `category:simulators:activehdl`: Aldec Active-HDL
- `category:simulators:cvc`: Tachyon CVC
- `category:simulators:ghdl`: GHDL
- `category:simulators:icarus`: Icarus Verilog (iverilog)
- `category:simulators:ius`: Cadence Incisive (IUS)
- `category:simulators:modelsim`: Mentor Modelsim
- `category:simulators:questa`: Mentor Questa
- `category:simulators:riviera`: Aldec Riviera-PRO
- `category:simulators:vcs`: Synopsys VCS
- `category:simulators:verilator`: Verilator
- `category:simulators:xcelium`: Cadence Xcelium
- `category:codebase:gpi`: relating to the GPI or one of the implementation
- `category:codebase:pygpi`: relating to the Python wrapper around the GPI (embed library and simulator module)
- `category:codebase:scheduler`: relating to the coroutine scheduler, triggers, or coroutine objects
- `category:codebase:test-runner`: relating to code for automating test runs (regression manager)
- `category:codebase:handle`: relating to handles or handle types (BinaryValue)
- `category:codebase:project-automation`: relating to included project automation (makefiles)
- `category:codebase:testbenching`: relating to testbenching components (Drivers, Monitors, etc.)
- `category:building`: relating to build C/C++ libraries and extension modules
- `category:packaging`: issues related to (PyPi) packaging, etc.
- `category:docs`: documentation issues and fixes
- `category:extensions`: cocotb extensions
- `category:performance`: performance topics
- `category:tests-ci`: continuous integration and unit tests

To help new contributors find a good issue to work on one more label is used (following [GitHub standard practices](#https://help.github.com/articles/helping-new-contributors-find-your-project-with-labels/)):
- `good first issue`: this issue is a good starting point for new contributors.
  The issue should give an actionable description of what to do to complete this task, along with contact information of a mentor for this task.

cocotb explicitly uses no priority labels, as experience indicates that they provide little value.

Issues and pull requests which are invalid, or where feedback is lacking for four weeks, should be closed.

## Cocotb Releases

cocotb aims to keep the `master` branch always in a releasable state.
At least four times a year an official release should be created.
It is the job of the maintainers to find a suitable time for a release, to communicate it to the community, and to coordinate it.

## Maintainers

Cocotb uses a shared maintainer model.
Most maintainers are experts in part of the cocotb codebase, and are primarily responsible for reviews in this area.

- Kaleb Barrett (@ktbarrett)
- Tomasz Hemperek (@themperek)
- Marlon James (@garmin-mjames)
- Colin Marquardt (@cmarqu)
- Philipp Wagner (@imphil)
- Eric Wieser (@eric-wieser)

Founders

- Chris Higgs (@chiggs)
- Stuart Hodgson (@stuarthodgson)

## Code of Conduct

The cocotb development community aims to be welcoming to everyone.
The [FOSSi Foundation Code of Conduct](https://www.fossi-foundation.org/code-of-conduct) applies.
Please contact any of the maintainers if you feel uncomfortable in the cocotb development community.
