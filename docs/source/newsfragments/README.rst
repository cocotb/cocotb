:orphan:

*********************
Writing Release Notes
*********************

We are using `towncrier <https://pypi.org/project/towncrier/>`_ to handle
our release notes, and this directory contains the input for it -
"news fragments" which are short files that contain a small
**ReST**-formatted text that will be added to the next version's
Release Notes page.

Writing Newsfragments
---------------------

Each file should be named like ``<ISSUE_OR_PR>.<TYPE>.rst``,
where ``<ISSUE_OR_PR>`` is an issue or a pull request number -
whatever is most useful to link to,
and ``<TYPE>`` is one of:

* ``feature``: New user-facing feature.
* ``bugfix``: A bug fix.
* ``doc``: Documentation improvement.
* ``removal``: Deprecation or removal of public API or behavior.
* ``change``: A change in public API or behavior.

In that file, make sure to use full sentences with correct case and punctuation.
Use "action" statements as much as possible.
If deprecating or removing something and there is an alternative, mention the alternative.
If changing behavior list both the new and old behavior;
and if there is a way to emulate the old behavior, mention it.
Avoid mentioning rationale or needless details and avoid talking to the reader.
Use Sphinx references (see https://sphinx-tutorial.readthedocs.io/cheatsheet/)
if you refer to added classes, methods etc.
In cases where there is more than one piece of news for a pull request,
split the news into multiple fragments (see below for details on how to do that).

Do not use a bullet point at the beginning of the file;
those are added automatically.
Each fragment file must be a single piece of news on a single line;
multi-line files will not render correctly.

Examples:

.. parsed-literal::

    Added :class:`TaskManager`.

.. parsed-literal::

    Deprecated passing ``name`` to the :class:`.Event` constructor. If you need to associate a name with an :class:`!Event`, subclass :class:`!Event` and add a ``name`` attribute.


Multiple Newsfragments per PR
-----------------------------

Multiple newsfragments of different ``<TYPE>`` can be added for a single ``<ISSUE_OR_PR>``.
Additional newsfragments of the same ``<TYPE>`` for a single ``<ISSUE_OR_PR>`` are
supported using the name format ``<ISSUE_OR_PR>.<TYPE>.<#>.rst``.

Example:

* ``<ISSUE_OR_PR>.bugfix.rst``
* ``<ISSUE_OR_PR>.bugfix.1.rst``
* ``<ISSUE_OR_PR>.removal.rst``


How Towncrier Works
-------------------

Towncrier automatically assembles a list of unreleased changes when building Sphinx (see :file:`docs/conf.py`),
meaning your notes will be visible in the documentation immediately after merging.

When performing a release, ``towncrier`` should be run independently (in cocotb's root directory),
which will delete all the merged newsfragments.
Make sure to commit the changes.

:file:`pyproject.toml` contains the configuration for towncrier.
