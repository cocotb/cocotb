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


cocotb Releases
===============

cocotb aims to keep the ``master`` branch always in a releasable state.
At least four times a year an official release should be created.
It is the job of the maintainers to find a suitable time for a release, to communicate it to the community, and to coordinate it.

Doing a Release
---------------

Release notes are always filed under the version being released, e.g. ``2.1.0``, never under a release candidate.
An rc is tagged from the very notes the final release will ship, so steps 1 and 2 are done once per release, before the first rc.

1. Run `Release 1: Prepare release <https://github.com/cocotb/cocotb/actions/workflows/release-1-prepare.yml>`__ with the version being released, e.g. ``2.1.0`` or ``2.1.1``.
2. Review, hand-edit if needed, and merge the release notes PR it opens.
   If a new series was branched off, also merge the "Start X.Y.0 development" PR it opens against ``master``.
3. Run `Release 2: Tag <https://github.com/cocotb/cocotb/actions/workflows/release-2-tag.yml>`__ with the version to tag, e.g. ``2.1.0rc1`` first and ``2.1.0`` later.
4. For a final release (not an rc): once PyPI publishing succeeds, review and merge the release notes backport PR opened automatically against ``master``, and the "Start X.Y.Z release cycle" PR opened against the release branch.

If a change lands on the release branch between an rc and the final release, fold it into the existing release notes section by hand and delete its newsfragment in the same PR.
"Release 2: Tag" refuses to tag while newsfragments are still pending on the branch, because they would not be covered by the release notes.

Doing a Release Manually
------------------------

Do this instead of the steps above if GitHub Actions isn't available, or a step needs to be redone with something non-standard.

1. Check out the release branch (``stable/<major>.<minor>``, e.g. ``stable/2.1`` for version ``2.1.1``), creating it from ``master`` first if this is the first release of the series:

   .. code-block:: bash

      VER_MAJOR_MINOR=2.1
      VER_FULL=$VER_MAJOR_MINOR.0

      # Only for the first release of a new series (major.minor)
      git fetch origin master
      git checkout -b stable/$VER_MAJOR_MINOR origin/master
      git push origin stable/$VER_MAJOR_MINOR

      # Otherwise:
      git fetch origin stable/$VER_MAJOR_MINOR
      git checkout stable/$VER_MAJOR_MINOR

2. Bump the ``VERSION`` file on ``master`` to the next minor release.

3. Generate the release notes and open a PR against the release branch for review, instead of committing directly:

   .. code-block:: bash

      nox -s release_notes
      git add docs/source/release_notes.rst docs/source/newsfragments
      git commit -m "Generate release notes for v$VER_FULL"
      git push origin HEAD:release-notes/$VER_FULL
      gh pr create --base stable/$VER_MAJOR_MINOR --title "Release notes for v$VER_FULL" --fill

4. Review, hand-edit if needed, and merge that PR.

5. Tag the merged commit and push it.
   Use the same tag for a release candidate, e.g. ``v2.1.0rc1``:

   .. code-block:: bash

      git fetch origin stable/$VER_MAJOR_MINOR
      git checkout stable/$VER_MAJOR_MINOR
      git tag -a v$VER_FULL -m "Release $VER_FULL"
      git push origin v$VER_FULL

6. For a final release only (not an rc): once PyPI publishing succeeds, backport the notes to ``master``:

   .. code-block:: bash

      git fetch origin master
      git checkout master
      git pull
      nox -s backport_release_notes -- --until=v$VER_FULL
      git add docs/source/release_notes.rst docs/source/newsfragments
      git commit -m "Backport release notes for v$VER_FULL to master"
      git push origin HEAD:backport-release-notes/$VER_FULL
      gh pr create --base master --title "Backport release notes for v$VER_FULL to master" --fill

7. Review and merge that PR too.

8. Bump the ``VERSION`` file on the release branch to the next patch version.

How Releases Work
-----------------

Releases are made by pushing an annotated ``vX.Y.Z`` tag; that push alone triggers the whole build, test, and PyPI publish pipeline (``.github/workflows/build-test-release.yml``), so it is the actual point of no return in the process above -- every step before it can be redone or abandoned freely.
The only thing that can stop a release after the tag exists is a protection rule on the ``pypi`` environment (see below).
That is also why "Release 2: Tag" checks before tagging that the release notes for the version exist on the branch and that no newsfragments are left pending.

Two situations are handled the same way:

-  **The first release of a new minor series** (e.g. ``2.1.0``): a new ``stable/2.1`` branch is created off ``master``.
-  **A patch release** on an existing series (e.g. ``2.1.1``): the existing ``stable/2.1`` branch is reused. Any fixes it needs must be backported there first, as described above.

`Release 1: Prepare release <https://github.com/cocotb/cocotb/actions/workflows/release-1-prepare.yml>`__ derives the release branch from the version and creates it from ``master`` if it doesn't exist yet -- but only when the version's patch component is ``0``, i.e. it's genuinely the first release of the series; otherwise a missing branch is treated as a typo and the workflow fails rather than guessing.
It then runs `towncrier <https://towncrier.readthedocs.io/>`_ on that branch (via ``nox -s release_notes``) to consume the pending newsfragments into ``docs/source/release_notes.rst``, and opens a PR with the result. Merging that PR is what marks the branch ready to tag, and is the manual gate before anything gets tagged -- there's no automated substitute for it by design.

`Release 2: Tag <https://github.com/cocotb/cocotb/actions/workflows/release-2-tag.yml>`__ tags the release branch's current HEAD as ``vX.Y.Z`` and pushes it, which triggers ``build-test-release.yml``: it builds the wheels and sdist, runs the full regression suite against them, and -- once that passes -- publishes to PyPI using Trusted Publishing and creates a GitHub Release for the tag.

The ``VERSION`` file names the release the current branch is working towards, as a full ``X.Y.Z``.
It feeds `setuptools-git-versioning <https://setuptools-git-versioning.readthedocs.io/>`_, which uses it to version the ``dev`` builds made from every commit that isn't tagged, and it is where ``nox -s release_notes`` takes the version to file the notes under.
It therefore has to move on whenever a branch starts working towards a different version: to the next minor on ``master`` when a series is branched off (done by "Release 1"), and to the next patch on the release branch once a final release is tagged (done by "Release 2").
Both are proposed as PRs, like everything else these workflows do.

``master``'s ``docs/source/release_notes.rst`` should always show the full release history, including patch releases, even though patch releases only ever run towncrier on a stable branch. For a **final** release (``vX.Y.Z``, no ``rc`` suffix), ``build-test-release.yml`` handles this automatically once publishing succeeds, by calling `Release 3: Backport release notes to master <https://github.com/cocotb/cocotb/actions/workflows/release-3-backport-notes.yml>`__: it copies the notes section that was just generated on the release branch back into ``master``, removes the newsfragments it consumed there so they aren't listed again under the next release, and opens a PR. Release candidates are skipped, since they ship the final release's notes rather than a section of their own.

The actual work is done by the ``backport_release_notes`` nox session, which can also be run locally:

.. code-block:: bash

   nox -s backport_release_notes -- --until=v$VER_FULL

It takes the finished section out of ``release_notes.rst`` as of the tag -- hand-edits included -- and inserts it into ``master``'s copy in version order, so that backporting a patch release of an older series after a newer series has been released puts it in the right place rather than at the top.
The newsfragments to drop are those the release consumed between ``--since`` and the tag.
``--since`` defaults to the point where the release branch forked from ``master``.
That covers every release made on the branch, not just this one, but the fragments an earlier release consumed were already removed from ``master`` by its own backport, so only this release's are left to delete.
The previous release tag would be a tighter boundary but the wrong one: a release candidate is tagged on the very notes the final release ships, so the tag before ``vX.Y.Z`` is ``vX.Y.ZrcN``, which comes *after* the commit that consumed the newsfragments.
Pass ``--since`` to narrow it down.

If the automatic backport PR needs to be regenerated, or a release from before this automation existed needs backporting, run the same "Release 3" workflow directly instead -- it also accepts ``since_ref``.

Release Automation Setup
------------------------

The release workflows do not use the default ``GITHUB_TOKEN``: a tag pushed with it does not start any workflow run (so nothing would ever be built or published), and pull requests created with it don't run any CI.
They authenticate as a GitHub App instead, which needs **Contents: Read and write** and **Pull requests: Read and write** on the repository, and to be able to push to ``master`` and ``stable/*`` if those branches are protected.
Its credentials are read from the repository secrets ``COCOTB_CI_REPOACCESS_APP_ID`` and ``COCOTB_CI_REPOACCESS_APP_PRIVATE_KEY``.

Publishing to PyPI runs in the ``pypi`` `environment <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>`__.
Adding required reviewers to that environment is the way to get a human confirmation step between the tag and the upload; without protection rules it publishes straight away.
The environment name has to match what `cocotb's Trusted Publishing configuration <https://pypi.org/manage/project/cocotb/settings/publishing/>`__ on PyPI expects -- either ``pypi``, or no environment at all.


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
