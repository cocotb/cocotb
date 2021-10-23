:orphan:

*********************
Writing Release Notes
*********************

We are using `towncrier <https://pypi.org/project/towncrier/>`_ to handle
our release notes, and this directory contains the input for it -
"news fragments" which are short files that contain a small
**ReST**-formatted text that will be added to the next version's
Release Notes page.

Each file should be named like ``<ISSUE_OR_PR>.<TYPE>.rst``,
where ``<ISSUE_OR_PR>`` is an issue or a pull request number -
whatever is most useful to link to,
and ``<TYPE>`` is one of:

* ``feature``: New user-facing feature.
* ``bugfix``: A bug fix.
* ``doc``: Documentation improvement.
* ``removal``: Deprecation or removal of public API or behavior.
* ``change``: A change in public API or behavior.

In that file, make sure to use full sentences with correct case and punctuation,
and do not use a bullet point at the beginning of the file.
Each fragment file should be a single piece of news on a single line;
multi-line files will not render correctly.
In cases where there is more than one piece of news for a pull request,
split the news into 2 fragments (see below for details on how to do that).
Use Sphinx references (see https://sphinx-tutorial.readthedocs.io/cheatsheet/)
if you refer to added classes, methods etc.

Additional newsfragments of the same ``<TYPE>`` for a single ``<ISSUE_OR_PR>`` are
supported, using the name format ``<ISSUE_OR_PR>.<TYPE>.<#>.rst``.

Example:

* ``<ISSUE_OR_PR>.bugfix.rst``
* ``<ISSUE_OR_PR>.bugfix.1.rst``

An example file could consist of the content between the marks:

--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<--8<
Summary of a new feature.

This is a second paragraph.
-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8-->8

Note that the last paragraph should be a normal sentence and not e.g. code,
because the issue number is appended there.

Towncrier automatically assembles a list of unreleased changes when building Sphinx,
meaning your notes will be visible in the documentation immediately after merging.
When performing a release, ``towncrier`` should be run independently (in cocotb's root directory),
which will delete all the merged newsfragments, and create new commits.
