# Cocotb Contribution Guidelines

Welcome to the cocotb development!
We are an inclusive community with the common goal of improving the cocotb, a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.
This guide explains how to contribute to cocotb, and documents the processes we agreed on to manage the project.
All processes in this document are designed to streamline the development effort, to avoid bottlenecks, and to ultimately give a pleasant experience to all involved.


## Getting Help

Cocotb is a diverse and challenging project to contribute to.
If you ever feel lost, out of your depth, or simply want to know more, the [cocotb Gitter channel](https://gitter.im/cocotb/Lobby) is actively watched by many cocotb users, contributors, and maintainers.
It is a good idea if you are unsure whether your problem or question is worthy of a Github Issue to first post it to the Gitter channel.
You may also ask questions in [Github issues](https://github.com/cocotb/cocotb/issues).
If you don't receive any response on the Gitter channel or a Github issue, or you want help privately, you may directly contact a [maintainer](#maintainers).


## What to Work On

There is *a lot* of work to do on this project, no matter your area of expertise or skill level.

If you are a beginner there are several [Github issues](https://github.com/cocotb/cocotb/issues) marked [`good first issue`](https://github.com/cocotb/cocotb/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22) you can look at.
There are also a number of things you can work on that aren't in Github issues and don't require in-depth knowledge of the cocotb internals.
They including the following:

* Documentation improvements
* Managing Github issues and the Gitter channel
* Testing and coverage improvements

Cocotb is still not perfect. There are plenty of [bug fixes](https://github.com/cocotb/cocotb/issues?q=is%3Aopen+is%3Aissue+label%3Atype%3Abug) and [features](https://github.com/cocotb/cocotb/issues?q=is%3Aopen+is%3Aissue+label%3Atype%3Afeature) that can be worked on.
Most of these are recorded as Github issues.


### Documentation

Cocotb's documentation is always open to improvements.
Improving documentation will help users better understand and use cocotb;
and may decrease the number of questions the Gitter channel and Github issue page.
Updating documentation requires knowledge of:

* [reStructuredText](https://docutils.sourceforge.io/rst.html)
* [Sphinx documentation generator](https://www.sphinx-doc.org/en/master/)
* [Markdown](https://www.markdownguide.org/)
* [How to architect documentation](https://documentation.divio.com/)

Some documentation should be located in the official documentation on [Read the Docs/RTD](https://docs.cocotb.org/en/latest/),
while the rest belongs on the [Wiki](https://github.com/cocotb/cocotb/wiki).
There are several ways to improve the documentation:

* Better documenting core functionality (RTD)
* Documenting common "gotchas" (RTD)
* Documenting difficult and niche use cases (Wiki)
* Documenting common design patterns (Wiki)
* Documenting internal components (Wiki)

See the documentation on [building the documentation](#building-documentation-locally) and the [guidelines on submitting pull requests](#patch-requirements).
Documentation improvements typically require no maintainer pre-approval; you can simply work on the documentation and open a pull request.
Documentation on the Wiki does not require a pull request; any user with a Github account can contribute to it.
Please be responsible with that power.


### Project Management

The cocotb project is [fairly popular](https://larsasplund.github.io/github-facts/verification-practices.html#frameworks) and the
[Gitter channel](https://gitter.im/cocotb/Lobby) and
[Github issues](https://github.com/cocotb/cocotb) page receive a fair amount of traffic;
which is only expected to increase.
People are needed to categorize issues and pull requests, and respond to questions.
Working this task is the quickest way to learn how cocotb works.
Tending to this task requires the following:

* people skills
* an understanding of the scope of cocotb
* general understanding about how cocotb works

Someone working this task should set notifications on the Gitter channel to be notified of any new comments.
They should also "watch" the Github repo by selecting the "Watching" notification level button in the upper right corner of the main Github page.
Finally, they should notify the maintainers that they are able and willing to accept questions.

To be able to add labels and close issues and PRs you will need special permissions.
Contact a [maintainer](#maintainer) if you are interested in receiving these permissions.
They will be granted according to the project's need and the requestor's familiarity with cocotb.
Once you have those permissions, see the guidelines on [managing issues and pull requests](#Managing-of-Issues-and-Pull-Requests).

This task can also be done without special repo permissions, by just commenting on the issue or PR.
This is especially helpful for Github issues about bugs.
If you can duplicate the bug or confirm the bug report is invalid, that helps maintainers *a lot*.


### Tests and Coverage

Cocotb has a suite of unit tests (located in the `tests` directory) and examples (located in the `examples` directory) which are functional acceptance tests.
If a pull request cannot pass *all* of these tests, it will likely be rejected.
To ensure cocotb only includes the highest quality code, these test should be exhaustive.
We use code coverage as a quantifiable metric of the "exhaustiveness" of these tests, and wish to improve this metric.

Working on this task requires a familiarity with:

* Cocotb's core functionality
* How to write Verilog and VHDL
* How to write cocotb tests in Python
* (Optionally) [codecov](https://docs.codecov.io/docs); coverage aggregator and Github bot
* (Optionally) the [coverage](https://coverage.readthedocs.io/en/latest/) module, for Python code coverage
* (Optionally) [gcov](https://gcc.gnu.org/onlinedocs/gcc/Gcov.html), for C++ code coverage
* (Optionally) [Github Actions](https://docs.github.com/en/free-pro-team@latest/actions), for automatic acceptance testing

Cocotb's regression tests can be improved by:

* Testing more of cocotb's core functionality
* Testing corner cases left out of the current set of tests (identified by looking at code coverage)
* Increasing the matrix of simulators, operating system, and Python installations tested in CI

Testing improvements don't require maintainer pre-approval, but require a pull request.
Please see the [guidelines on submitting pull requests](#patch-requirements).


### Features

Cocotb is still in development and new features are still welcome and appreciated;
as long as they stay [in scope](#Architecture-and-Scope-of-Cocotb).
Cocotb is comprised of several major codebases, each requiring different sets of skills and development process.
Instead of including that breakdown here, it is done in the [internal documentation](https://github.com/cocotb/cocotb/wiki/cocotb-Internals).

Small improvements to existing features generally do not require maintainer pre-approval.
Large changes, approximately >150 LOC changed, and new features generally require maintainer pre-approval.
If a change is deemed too large for the main repo, or out of scope,
please feel free to make it an [extension](https://docs.cocotb.org/en/latest/extensions.html).

***New features must not break existing features.***

Feature changes require full coverage of the added feature.
This likely requires adding new unit tests to the `tests` directory.
Issue-specific test directories will not be accepted, unless a special HDL entity is required.
Instead, place the test in an existing test suite (`test_cocotb`, `test_discovery`, etc.).

Features should generally follow the following design principles:

* Something the user cannot do without assistance of cocotb-specific code
* Orthogonal to existing features
* Easily composed with existing features
* Limited in scope and impervious to scope creep


### Bugfixes

**!WARNING!** Bugfixing cocotb is not for the faint of heart!

Bugs happen.
cocotb supports many simulators that have inconsistent support for the procedural interfaces cocotb depends on,
and it has a number of features that aren't wholly tested yet.
There are likely many bugs lurking, waiting to be found;
which is why increasing testing and code coverage is important.
Working on bugfixing can be very challenging, depending on the cause of the bug.
In general, bugfixing requires knowledge of:

* How cocotb works
* [cocotb's debugging utilities](https://github.com/cocotb/cocotb/wiki/Debugging-HOW-TOs#cocotb-debugging-functionality)
* (Optional) Simulator interfaces (VPI, VHPI, and FLI)
* (Optional) Python debugging tools ([pdb](https://github.com/cocotb/cocotb/wiki/Debugging-HOW-TOs#using-a-remote-python-debugger), [dowser](https://github.com/cocotb/cocotb/wiki/Debugging-HOW-TOs#debugging-python-memory-usage))
* (Optional) C/C++ debugging tools ([gdb](https://github.com/cocotb/cocotb/wiki/Debugging-HOW-TOs#using-a-remote-cc-debugger), [valgrind](https://github.com/cocotb/cocotb/wiki/Debugging-HOW-TOs#debugging-cc-memory-usage))
* (Optional) Specific simulators (sometimes the bug exists in the simulator and not cocotb)

Fixing a bug follows the procedure:

1. Locate buggy behavior, make a Github issue
    * Maintainers may be able to offer more information, confirm it as a bug, or confirm it as expected behavior
2. Make a Minimum Reproducible Failing Example (MRFE, pronounced like Murphy, like the law :)
    * Confirms the bug
    * Add to [regressions](#running-tests-locally)
3. Open a new draft pull request with the MRFE test
    * It should cause CI to fail
4. Determine scope of the bug, and add that detail to the pull request
    * Which simulators/interfaces are affected?
    * Which Python versions?
    * Which operating systems?
5. Determine the cause of the bug, and add that detail to the pull request
    * May require Python or C debugging, or the builtin cocotb debugging utilities
6. Make a fix, and push it up on the PR branch
    * It should cause the CI to pass
    * The fix should not break other existing functionality

Details on how to debug cocotb can be found on the [Wiki](https://github.com/cocotb/cocotb/wiki/Debugging-HOW-TOs).


### Deprecations and Removals

Cocotb's treatment of deprecations and removal follows guidelines laid out [here](https://symfony.com/doc/current/setup/upgrade_major.html#make-your-code-deprecation-free).
Deprecations serve the following purposes:

* Remove legacy code that has been deemed out of scope
* Remove support for a simulator, OS, or Python version that is past end-of-life
* Remove potentially dangerous, broken, and misunderstood interfaces (usually accompanied with a superior alternative)

Deprecations can be incorporated at any time.
They are implemented in Python by [issuing a `DeprecationWarning`](https://docs.python.org/3/library/warnings.html#warnings.warn)
or using the [`@deprecated`](cocotb/_deprecation.py) decorator.
In C++ code, deprecations are implemented by [issuing a LOG_WARN](https://docs.cocotb.org/en/stable/generated/file/gpi__logging_8h.html?highlight=LOG_WARN#c.LOG_WARN) with `DEPRECATED` in the message.

Removals only occur on major version bumps.
One can create removal pull requests at any time, on the condition they will not be accepted until the next release is known to be a major version release.


### Breaking Changes

Breaking changes are changes to the interface or behavior of a user-facing entity.
They are necessary when a user-facing interfaces are broken in a way that cannot be changed without changing the behavior of user's code.
In these situations it is ideal to be able to implement a switch between new better behavior and the old broken behavior.
On major version bumps, this switch will be deprecated and the new behavior will become the default.

In cases where behavioral switches are not easy to implement, breaking changes will attempt to be broadcasted to user by [issuing a `DeprecationWarning`](https://docs.python.org/3/library/warnings.html#warnings.warn) when the to-be-changed behavior is invoked.
Before major releases, pending breaking changes will be incorporated.

One can create pull requests with breaking changes at any time, on the condition they will not be accepted until the next release is known to be a major version release.


## Setting Up a Development Environment

Assuming you have used cocotb prior to reading this guide, you will already have the cocotb [installation prerequisites](https://docs.cocotb.org/en/latest/install.html) and standard development tools (editor, shell, git, etc.) installed.

First, you should [fork and clone](https://guides.github.com/activities/forking/) the cocotb repo to your machine.
This will allow you to make changes to the cocotb source code, create pull requests, and run regressions and build documentation locally.

Additionally, you will need [doxygen](https://www.doxygen.nl/index.html), for building documentation;
[nox](https://pypi.org/project/nox/), for building documentation and running regression tests;
and [pre-commit](https://pre-commit.com/), to check your changes before committing them.

We recommend if you are using a Linux distribution to use your system package manager to install doxygen.
Likewise, doxygen can be installed using the homebrew package manager on Mac OS.
Windows contributors should download a binary distribution installer from the main website.

`nox` and `pre-commit` are Python projects and can be installed with `pip`:

```command
pip install nox pre-commit
```

To enable pre-commit run the following command at the root of the cloned project to install the git hooks.
The first run of pre-commit will build an environment for you, so it may take a while.
Following runs should be much quicker.

```command
pre-commit install
```

When committing, pre-commit's hook will run, checking your changes for formatting, code smells, etc.
You will see the lists of checks printed and whether they passed, were skipped, or failed.
If any of the checks fail, it is recommended to fix them before opening a pull request,
otherwise the pull request checks will fail as well.

Now you are ready to contribute!


## Running Tests Locally

First, [set up your development environment](#setting-up-a-development-environment).

Our tests are managed by `nox`, which runs both `pytest` tests and our system of makefiles.
The regression does not end on the first failure, but continues until all tests in the `/tests` and `/examples` directories have been run.

To run the tests locally with `nox`, issue the following command.

```command
nox -s dev_test
```

At the end of the regression, if there were any test failures, the tests that failed will be printed.
If the tests succeed you will see the message `Session tests was successful` printed in green.

By default the `dev_test` nox session runs all simulator-agnostic tests, as well as all tests which require a simulator and can be run against Icarus Verilog.
Icarus Verilog must be installed.

The simulator and the toplevel language can be changed by setting the environment variables [`SIM`](https://docs.cocotb.org/en/latest/building.html#var-SIM) and [`TOPLEVEL_LANG`](https://docs.cocotb.org/en/latest/building.html#var-TOPLEVEL_LANG).
Alternatively, the simulator-specific nox sessions can be used, as described below.

### Selecting a Language and Simulator for Regression

cocotb can be used with multiple simulators, and can run tests against all of them.
Nox provides a session for each valid simulator/language/GPI interface combination, from which one or multiple sessions can be selected.

The following examples are good starting points;
refer to the [nox command-line usage documentation](https://nox.thea.codes/en/stable/usage.html) for more information.

```command
# List all available sessions.
nox -l

# Run all simulator-agnostic tests.
nox -s dev_test_nosim

# Run the simulator-specific tests against Xcelium, using a VHDL toplevel and
# the VHPI interface.
nox -s "dev_test_sim(sim='xcelium', toplevel_lang='vhdl', gpi_interface='vhpi')"

# Run all simulator-specific tests against Icarus Verilog and GHDL.
# Both simulators must be installed locally.
nox -k "dev_test_sim and (icarus or ghdl)"
```

### Running Individual Tests Locally

Each test under `/tests/test_cases/*/` and `/examples/*/tests/` can be run individually.
This is particularly useful if you want to run a particular test that fails the regression.

First you must install cocotb from source by navigating to the project root directory and issuing the following command:

```command
python -m pip install .
```

On Windows, you must instead install cocotb from source like so:

```command
python -m pip install --global-option build_ext --global-option --compiler=mingw32 .
```

Once that has been done, you can navigate to the directory containing the test you wish to run.
Then you may issue an [appropriate](https://docs.cocotb.org/en/latest/building.html#makefile-based-test-scripts) `make` command.
For example, if you want to test with Icarus using Verilog sources:

```command
make SIM=icarus TOPLEVEL_LANG=verilog
```


## Building Documentation Locally

First, [set up your development environment](#setting-up-a-development-environment).

Documentation is built locally using `nox`.
The last message in the output will contain a URL to the documentation you just built.
Simply copy and paste the link into your browser to view it.
The documentation will be built in the same location on your hard drive on every run, so you only have to refresh the page to see new changes.

To build the documentation locally on Linux or Mac, issue the following command:

```command
nox -e docs
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


## Maintainer Pre-approval

After making changes to cocotb, changes must be approved by at least one maintainer before being included.
Out-of-scope and breaking changes ***will not be accepted***.
Also a maintainer could object to a change due to implementation approach or code quality reasons.
To potentially save you frustration and time, it is a good idea to get maintainer pre-approval on the task before starting it.

The best way to get maintainer pre-approval is to make a [Github issue](https://github.com/cocotb/cocotb/issues).
These issues can be a place for maintainers, as well as other users, to voice opinions on a proposed change before the task is worked.
You may also propose changes on the [Gitter channel](https://gitter.im/cocotb/Lobby) or by directly contacting a [maintainer](#maintainer).


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
- All code must follow the established coding standards:
   - For Python code, follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.
   - For C++ code, follow the [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html) but with 4 space indentation.
     You can run the following command to automatically format the modified file to match the standard:
     ```command
     clang-format -i <file>
     ```
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
- Marlon James (@marlonjames)
- Colin Marquardt (@cmarqu)
- Philipp Wagner (@imphil)
- Eric Wieser (@eric-wieser)

Founders

- Chris Higgs (@chiggs)
- Stuart Hodgson (@stuarthodgson)

### Getting in Contact with a Maintainer

All of the maintainers are active on the [Gitter channel](https://github.com/cocotb/cocotb).
They prefer inquiries go through direct messages on Gitter,
or by mentioning them in the main [cocotb Gitter channel](https://gitter.im/cocotb/Lobby) using `@{maintainer name}`.
Maintainers are unpaid volunteers, so it might take a while for a maintainer to get back to you.


## Code of Conduct

The cocotb development community aims to be welcoming to everyone.
The [FOSSi Foundation Code of Conduct](https://www.fossi-foundation.org/code-of-conduct) applies.
Please contact any of the maintainers if you feel uncomfortable in the cocotb development community.
