##################################
Welcome to Cocotb's documentation!
##################################

..
   This documentation tries to follow https://www.divio.com/blog/documentation/ (Daniele Procida)
   Other media about the same topic:
   - https://ep2018.europython.eu/media/conference/slides/get-your-documentation-right.pdf
   - https://www.youtube.com/watch?v=t4vKPhjcMZg
   - A good example: http://docs.django-cms.org/en/latest/contributing/documentation.html#contributing-documentation

   See also https://github.com/cocotb/cocotb/wiki/Howto:-Writing-Documentation

.. toctree::
   :maxdepth: 2

   introduction

.. todo::
   Move "Contributors" section to "Development & Community"

#########
Tutorials
#########

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

   quickstart
   endian_swapper
   ping_tun_tap
   hal_cosimulation
   examples


#############
How-to Guides
#############

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

   writing_testbenches
   coroutines
   triggers
   testbench_tools

.. todo::
   - Add WaveDrom, IPython sections
   - How to deal with existing Verification IP?
   - Point to https://github.com/cocotb/cocotb/wiki/Code-Examples


##########
Key topics
##########

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

   troubleshooting

.. todo::
   - Add some info from :doc:`coroutines`
   - Add GPI section
   - Explain ReadOnly/ReadWrite/... phases
   - Add pitfall from https://github.com/cocotb/cocotb/issues/526#issuecomment-300371629 to troubleshooting


#########
Reference
#########

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

   building
   Python Code Library Reference <library_reference>
   C/C++ Code Library Reference <library_reference_c>
   simulator_support
   extensions

.. todo::
   - *Maybe* add a glossary (Coroutine, Driver, Monitor, Scoreboard, HDL, RTL, GPI, V(H)PI, FLI, VIP, UVM, MDV, DUT/DUV)

#######################
Development & Community
#######################

.. toctree::
   :maxdepth: 1
   :caption: Development & Community

   roadmap

.. todo::
   Add "Join us online" and "Contributing"


#############
Release Notes
#############

.. toctree::
   :maxdepth: 1
   :caption: Release Notes

   release_notes


#######
Indices
#######

* :ref:`Index of Classes, Methods, Variables etc.<genindex>`
* :ref:`Index of Python Modules <modindex>`
