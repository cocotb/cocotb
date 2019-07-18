Cocotb Contribution Guidelines
==============================

Welcome to the cocotb development!
We are an inclusive community with the common goal of improving the cocotb, a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.
This guide explains how to contribute to cocotb, and documents the processes we agreed on to manage the project.
All processes in this document are designed to streamline the development effort, to avoid bottlenecks, and to ultimately give a pleasant experience to all involved.

Architecture and Scope of Cocotb
--------------------------------

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


How to Get Changes Merged
-------------------------

Have you fixed a bug in cocotb, or want to add new functionality to it?
Cocotb follows the typical [GitHub flow](https://guides.github.com/introduction/flow/) and makes use of pull requests and reviews.
Follow the steps below to get your changes merged, i.e. integrated into the main cocotb codebase.

1. Create an issue ticket on [cocotb's GitHub issue tracker](https://github.com/potentialventures/cocotb/issues) describing the problem.
   Issues are also a good place to discuss design options with others before writing code.
2. [Fork](https://help.github.com/articles/fork-a-repo/) the [cocotb GitHub repository](https://github.com/potentialventures/cocotb) into your personal namespace.
3. Create a new branch off the `master` branch for your set of changes.
   Use one branch per "topic," i.e. per set of changes which belong together.
4. Create one or multiple commits to address the issue.
   Make sure to read and follow the [Patch Requirements](#patch-requirements) when preparing your commits.
5. Create new [pull request (PR)](https://github.com/potentialventures/cocotb/pulls).
6. When you submit (or update) the pull request, a suite of regression tests will run.
   If any of them turns "red," i.e. reports a failure, you most likely need to fix your code before it can be merged.
7. The pull request needs to be reviewed by at least one maintainer.
   We aim to give feedback to all pull requests within a week, but as so often, life can get in the way.
   If you receive no feedback from a maintainer within that time, please contact him/her directly (e.g. on [Gitter](https://gitter.im/cocotb) or email). You can find a [list of all maintainers](#maintainers) and their main area of expertise [below](#maintainers).
   If a maintainer asks you to explain or modify code, try to do so.
8. Once your code has at least one positive review from a maintainer and no maintainer strongly objects it your code is ready to be merged into the `master` branch.


Patch Requirements
------------------

All changes which should go into the main codebase of cocotb must follow this set of requirements.

- The code must be within the [scope of cocotb](#architecture-and-scope-of-cocotb).
- All code must be licensed under the [Revised BSD License](https://github.com/potentialventures/cocotb/blob/master/LICENSE).
  By contributing to this project you signal your agreement with these license terms.
- All code must follow the established coding standards.
  For Python code, follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.
- All code must pass existing tests.
  New functionality must be accompanied by tests, and bug fixes should add tests to increase the test coverage and prevent regressions.
- If code changes or enhances documented behavior the documentation should be updated.
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


Managing of Issues and Pull Requests
------------------------------------

The cocotb project makes use of GitHub labels attached to issues and pull requests to structure the development process.
Each issue and pull request can have multiple labels assigned.

The `type` labels define the type of issue or PR:
- `type:bug`: a bug in existing functionality
- `type:feature`: new functionality
- `type:question`: a support question

The `status` labels give a quick impression of the current status of the issue or PR:
- `status:worksforme`: the issue it not reproducible, or intended behavior (i.e. not a bug)
- `status:on-hold`: further progress is blocked by a dependency, e.g. other code which must be commited first.
- `status:needinfo`: feedback from someone is required. The issue/PR text gives more details.
- `status:duplicate`: the same issue is already being handled in another issue/PR.

For the use in pull requests the following additional status labels are defined:
- `status:review-needed`: this PR needs at least one review
- `status:changes-requested`: changes are requested to the code
- `status:ready-for-merge`: this PR is ready (according to the [Patch Requirements](#patch-requirements)) to be merged

The `category` labels help maintainers to filter issues which are relevant to their area of expertise:
- `category:windows`: Microsoft Windows-specific issues
- `category:simulators`: simulator support, including VPI/GPI/etc.
- `category:packaging`: issues related to (PyPi) packaging, etc.
- `category:docs`: documentation issues and fixes

To help new contributors find a good issue to work on one more label is used (following [GitHub standard practices](#https://help.github.com/articles/helping-new-contributors-find-your-project-with-labels/)):
- `good first issue`: this issue is a good starting point for new contributors.
  The issue should give an actionable description of what to do to complete this task, along with contact information of a mentor for this task.

cocotb explicitly uses no priority labels, as experience indicates that they provide little value.

Issues and pull requests which are invalid, or where feedback is lacking for four weeks, should be closed.

Cocotb Releases
---------------

cocotb aims to keep the `master` branch always in a releasable state.
At least four times a year an official release should be created.
It is the job of the maintainers to find a suitable time for a release, to communicate it to the community, and to coordinate it.


Maintainers
-----------

Cocotb uses a shared maintainer model.
Most maintainers are experts in part of the cocotb codebase, and are primarily responsible for reviews in this area.

- Julius Baxter (@juliusbaxter)
- Luke Darnell (@lukedarnell)
- Tomasz Hemperek (@themperek)
- Chris Higgs (@chiggs).
  Founder of cocotb.
- Stuart Hodgson (@stuarthodgson).
  Founder of cocotb.
- Philipp Wagner (@imphil)

Code of Conduct
---------------

The cocotb development community aims to be welcoming to everyone.
The [FOSSi Foundation Code of Conduct](https://www.fossi-foundation.org/code-of-conduct) applies.
Please contact any of the maintainers if you feel uncomfortable in the cocotb development community.
