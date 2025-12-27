#################
Welcome to cocotb
#################

..
   This documentation tries to follow https://diataxis.fr/
   Other media about the same topic:
   - https://ep2018.europython.eu/media/conference/slides/get-your-documentation-right.pdf
   - https://www.youtube.com/watch?v=t4vKPhjcMZg
   - A good example: http://docs.django-cms.org/en/latest/contributing/documentation.html#contributing-documentation

   See also https://github.com/cocotb/cocotb/wiki/Howto:-Writing-Documentation

***************
What is cocotb?
***************

cocotb enables users to test and verify their chip designs in `Python <https://www.python.org>`_ as opposed to VHDL, (System)Verilog, or other EDA-specific languages.


***********
Why cocotb?
***********

cocotb was specifically designed to lower the overhead of creating a testbench.
But it is still capable of -- and encourages -- reuse and randomized testing for building larger, more complex testbenches.

Python offers many advantages over languages traditionally used for test and verification, such as VHDL or (System)Verilog.

* Writing Python is **fast** - it's a very productive language.
* It's **easy** to interface to other languages from Python.
* Python has a huge library of existing code to **reuse**.
* Python is **interpreted** - tests can be edited and re-run without having to recompile the design or the testbench.
* Python is **popular** - far more engineers know Python than SystemVerilog or VHDL.

cocotb supports :ref:`most popular simulators <simulator-support>` on :ref:`most relevant platforms <platform-support>`.

When writing cocotb testbenches, users will typically not have to write any :term:`HDL`.

cocotb has built-in support for integrating with continuous integration systems,
such as Jenkins, GitLab, etc. through standardized, machine-readable test reporting formats.

cocotb is provided free of charge under the `BSD License <https://en.wikipedia.org/wiki/BSD_licenses#3-clause_license_(%22BSD_License_2.0%22,_%22Revised_BSD_License%22,_%22New_BSD_License%22,_or_%22Modified_BSD_License%22)>`_
and is hosted publicly on `GitHub <https://github.com/cocotb/cocotb>`_.


*********************
How does cocotb work?
*********************

cocotb is a **co**\ routine-based **co**\ simulation **t**\ est\ **b**\ ench environment.

This means that when the design is simulated, cocotb runs as a cosimulation using one of the procedural interfaces (:term:`VPI`, :term:`VHPI`, or :term:`FLI`).
A Python interpreter is embedded into the running simulator process to provide a Python execution environment.
A :doc:`Python library <library_reference>`
and `coroutine <https://en.wikipedia.org/wiki/Coroutine>`_\ -based concurrency system are built on top of the procedural interfaces to interact with the simulated design in a Pythonic way.

.. image:: diagrams/svg/cocotb_overview.svg


**************
Who is cocotb?
**************

cocotb is a Free and Open Source project and is developed collaboratively by its `contributors <https://github.com/cocotb/cocotb/graphs/contributors>`_ and :ref:`maintainers`.
cocotb has many serious commercial users and sponsors.
See `cocotb.org <https://cocotb.org>`_ for more details.


.. toctree::
   :maxdepth: 1
   :hidden:

   install
   quickstart

..
   Tutorials - lessons that take the reader by the hand through a series of steps to complete a project
   (Example: kid cooking; learning-oriented)

   - learning by doing
   - getting started
   - inspiring confidence
   - repeatability
   - immediate sense of achievement
   - concreteness, not abstraction
   - minimum necessary explanation
   - no distractions

.. toctree::
   :maxdepth: 1
   :caption: Tutorials
   :name: tutorials
   :hidden:

   examples


..
   How-To Guides - guides that take the reader through the steps required to solve a common problem
   (Example: recipe; problem-oriented)

   - a series of steps
   - a focus on the goal
   - addressing a specific question
   - no unnecessary explanation
   - a little flexibility
   - practical usability
   - good naming

.. toctree::
   :maxdepth: 1
   :caption: How-to Guides
   :name: howto_guides
   :hidden:

   writing_testbenches
   runner
   coroutines
   triggers
   custom_flows
   rotating_logger
   extensions
   upgrade-2.0
   update_indexing

.. todo::
   - Add IPython section
   - How to deal with existing Verification IP?
   - Point to https://github.com/cocotb/cocotb/wiki/Code-Examples


..
   Explanation (Background, Discussions) - discussions that clarify and illuminate a particular topic
   (Example: history of cooking; understanding-oriented)

   - giving context
   - explaining why
   - multiple examples, alternative approaches
   - making connections
   - no instruction or technical description

.. toctree::
   :maxdepth: 1
   :caption: Key topics
   :name: key_topics
   :hidden:

   install_devel
   troubleshooting
   timing_model

.. todo::
   - Move section "How does cocotb work?" from Introduction to here
   - Add some info from :doc:`coroutines`
   - Add GPI section


..
   Reference - technical descriptions of the machinery and its operation
   (Example: Wikipedia pages of ingredients; information-oriented)

   - structure
   - consistency
   - description
   - accuracy

.. toctree::
   :maxdepth: 1
   :caption: Reference
   :name: reference
   :hidden:

   building
   Python Code Library Reference <library_reference>
   GPI Library Reference <library_reference_c>
   simulator_support
   platform_support
   refcard

.. toctree::
   :maxdepth: 1
   :caption: Development & Community
   :name: development_community
   :hidden:

   support
   contributing
   developing
   maintaining
   contributors
   roadmap
   release_notes
   further_resources

.. todo::
   - merge `further_resources` into Contributing

.. toctree::
   :maxdepth: 1
   :caption: Index
   :name: index
   :hidden:

   Classes, Methods, Variables etc. <genindex>
   Python Modules <py-modindex>
   glossary
