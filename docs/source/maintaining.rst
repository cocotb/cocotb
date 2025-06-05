******************
Maintaining cocotb
******************

This section describes how to maintain cocotb, i.e., the more or less frequent tasks performed by the :ref:`cocotb maintainers <maintainers>`.

Managing of Issues and Pull Requests
====================================

The cocotb project makes use of GitHub labels attached to issues and pull requests to structure the development process.
Each issue and pull request can have multiple labels assigned.

The ``type`` labels define the type of issue or PR:

-  ``type:bug``: a bug in existing functionality
-  ``type:feature``: new functionality
-  ``type:cleanup``: cleanup or refactoring on code, documentation, or other areas
-  ``type:deprecation``: API that should warn and eventually be removed
-  ``type:change``: an API breaking change that isn't a deprecation or removal
-  ``type:backport``: a backport of another PR from master onto a stable branch
-  ``type:task``: a generic label for anything that doesn't fall into the above

The ``status`` labels give a quick impression of the current status of the issue or PR:

-  ``status:worksforme``: the issue it not reproducible, or intended behavior (i.e. not a bug)
-  ``status:blocked``: further progress is blocked by a dependency, e.g. other code which must be committed first.
-  ``status:needs-info``: feedback from someone is required. The issue/PR text gives more details.
-  ``status:duplicate``: the same issue is already being handled in another issue/PR.
-  ``status:close?``: issues which can probably be closed, but need a second pair of eyes
-  ``status:needs-proprietary-testing``: Help needed testing on a proprietary tool
-  ``status:out-of-scope``: An issue or PR that was closed because the feature or bug was deemed to be out of scope

For the use in pull requests the following additional status labels are defined:

-  ``status:needs-review``: this PR needs at least one review
-  ``status:ready-for-merge``: this PR is ready (according to the `Patch Requirements <#patch-requirements>`__) to be merged
-  ``status:needs-rebase``: needs a git rebase
-  ``status:needs-newsfragment``: Needs a towncrier newsfragment for the changelog
-  ``status:needs-test``: needs tests written
-  ``status:needs-proprietary-testing``: needs testing the change in a simulator we don't have access to

We occasionally find bugs in upstream projects, such as simulators, Python dependencies, CI tools, etc.
The following labels are used for those issues.

-  ``upstream``: marks the issue as being a issue with an upstream project
-  ``status:needs-upstream-report``: the issue has been diagnosed as an upstream issue, but no upstream report has been filed
-  ``status:upstream-report-filed``: the issue has been reported upstream

The ``category`` labels help maintainers to filter issues which are relevant to their area of expertise:

-  ``category:OS:MacOS``: Mac OS/OS X specific issues
-  ``category:OS:Linux``: Linux specific issues
-  ``category:OS:Windows``: Microsoft Windows-specific issues
-  ``category:simulators``: simulator support, including VPI/GPI/etc.
-  ``category:simulators:activehdl``: Aldec Active-HDL
-  ``category:simulators:cvc``: Tachyon CVC
-  ``category:simulators:ghdl``: GHDL
-  ``category:simulators:icarus``: Icarus Verilog (iverilog)
-  ``category:simulators:ius``: Cadence Incisive (IUS)
-  ``category:simulators:modelsim``: Mentor Modelsim
-  ``category:simulators:nvc``: NVC
-  ``category:simulators:questa``: Mentor Questa
-  ``category:simulators:riviera``: Aldec Riviera-PRO
-  ``category:simulators:vcs``: Synopsys VCS
-  ``category:simulators:verilator``: Verilator
-  ``category:simulators:xcelium``: Cadence Xcelium
-  ``category:codebase:gpi``: relating to the GPI or one of the implementation
-  ``category:codebase:pygpi``: relating to the Python wrapper around the GPI (embed library and simulator module)
-  ``category:codebase:scheduler``: relating to the coroutine scheduler
-  ``category:codebase:triggers``: related to triggers
-  ``category:codebase:tasks``: related to tasks or coroutines
-  ``category:codebase:tests``: relating to code for automating test runs (regression manager)
-  ``category:codebase:handle``: relating to handles
-  ``category:codebase:types``: relating to modelling types
-  ``category:codebase:project-automation``: relating to included project automation (makefiles, Python runner)
-  ``category:building``: relating to build C/C++ libraries and extension modules
-  ``category:packaging``: issues related to (PyPi) packaging, etc.
-  ``category:docs``: documentation issues and fixes
-  ``category:hardware-in-the-loop``: relating to real-life hardware (HIL)
-  ``category:performance``: performance topics
-  ``category:ci-free``: continuous integration and unit tests
-  ``category:meta``: cocotb repo, maintainers, or community
-  ``category:extensions``: cocotb extension modules
-  ``category:debugging``: debugging features

To help new contributors find a good issue to work on one more label is used (following `GitHub standard practices <#https://help.github.com/articles/helping-new-contributors-find-your-project-with-labels/>`__):

-  ``good first issue``: this issue is a good starting point for new contributors.
   The issue should give an actionable description of what to do to complete this task, along with contact information of a mentor for this task.

cocotb explicitly uses no priority labels, as experience indicates that they provide little value.

Issues and pull requests which are invalid, or where feedback is lacking for four weeks, should be closed.


Cocotb Releases
===============

cocotb aims to keep the ``master`` branch always in a releasable state.
At least four times a year an official release should be created.
It is the job of the maintainers to find a suitable time for a release, to communicate it to the community, and to coordinate it.


Backport Changes
================

All changes should generally be merged into the ``master`` branch first.
If those changes are also needed in a different branch, e.g., a stable branch, they need to be backported.
PRs can be backported fully automated through GitHub, or semi-automated with the ability to resolve merge conflicts.
Start with the automated backport process, and fall back to the manual one if necessary.

Automated PR Backports
----------------------

The backporting process starts from an open or already merged PR, typically targeting the ``master`` branch.
This PR can then be ported over to any of the ``stable/*`` branches.

1. Open the *source PR* you'd like to backport on GitHub.
2. Add the label ``backport-to:STABLE_BRANCH_NAME``, e.g. ``backport-to:1.9`` to backport a change to the branch ``stable/1.9``.
3. If not done yet: Merge the source PR.

Once the source PR is merged, backport automation (in GitHub Actions) will kick in.

* If the backport can be performed automatically (i.e., there are no merge conflicts), a new PR is opened against the stable branch.
* Otherwise, a comment is left in the source PR with instructions how to perform a manual backport. Follow the instructions below to continue.

Manual PR Backport
------------------

The most convenient way to backport a PR is using the `Backport CLI Tool <https://github.com/sorenlouv/backport/>`_, which also powers the automated backport process.

1. Install `npx` on your machine.
2. Configure authentication for Backport, as described at `in their documentation <https://github.com/sorenlouv/backport/blob/main/docs/config-file-options.md#global-config-backportconfigjson>`_.
3. In the *master* branch of the cocotb source tree run ``npx backport --pr MY_SOURCE_PR``.

Answer questions as necessary.
In case of a merge conflict, Backport will ask for a manual conflict resolution.
This resolution needs to happen in the separate backport repository, typically located at ``~/.backport/repositories/cocotb/cocotb``.

Backport will create a branch in your fork of the cocotb repository, and create a pull request to merge this branch into the selected stable branch, just like in the automated process.
