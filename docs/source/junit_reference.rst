.. _junit-reference:

****************************
JUnit Tests Report Reference
****************************

Result XML files are compatible with `Jenkins xUnit schema in Jenkins version 2.4.0
<https://github.com/jenkinsci/xunit-plugin/blob/xunit-2.4.0/src/main/resources/org/jenkinsci/plugins/xunit/types/model/xsd/junit-10.xsd>`_
and with JUnit XML test report files from pytest when used with ``junit_family=xunit2`` pytest option.
This allow to support wide range of different CI environments like GitHub Actions, GitLab CI, Jenkins CI and others.
However, only common fields are supported.


.. _junit-attributes:

Attributes
==========

Only a subset of XML elements and attributes from `Jenkins xUnit schema version 2`_ are supported.


.. _junit-attributes-testsuites:

testsuites
----------

The ``root`` of the XML document. It contains list of ``testsuite`` XML elements.

List of supported XML attributes:

* ``name`` - name of test suites, default is ``cocotb tests`` or ``pytest tests``.

Example:

.. code:: xml

    <testsuites name="cocotb tests">
    </testsuites>


.. _junit-attributes-testsuite:

testsuite
---------

It contains list of ``testcase`` XML elements.

List of supported XML attributes:

* ``name`` - name of test suite based on name of Python module where tests are defined.
* ``errors`` - total number of errors from all tests reported in this test suite.
* ``failures`` - total number of failed tests reported in this test suite.
* ``skipped`` - total number of skipped tests reported in this test suite.
* ``tests`` - total number of tests reported in this test suite.
* ``time`` - total wall time of all tests in this test suite in seconds.
* ``timestamp`` - date and time of when the test suite run was executed (in the ISO 8601 format with the UTC timezone).
* ``hostname`` - name of machine where the test suite run was executed.

.. note::

    The `Jenkins xUnit schema version 2`_ doesn't allow to have ``file`` and ``line`` as XML attributes in ``testcase`` XML element.
    They are part of :ref:`junit-attributes-property` XML element.

.. note::

    When generating JUnit XML file from pytest, it is possible to include ``file`` and ``line`` as XML attributes
    in ``testcase`` XML element by setting the pytest ``junit_family`` to ``xunit1``:

    .. code:: shell

        pytest --override-ini=junit_family=xunit1 --junit-xml=junit.xml ...

Example:

.. code:: xml

    <testsuite name="test_dff" errors="0" failures="1" skipped="1" tests="3" time="0.001" timestamp="2025-12-28T12:52:42.287738+00:00" hostname="d9019dc0cfcf">
    </testsuite>


.. _junit-attributes-testcase:

testcase
--------

Reported test.

It may contain ``properties``, ``skipped``, ``failure``, ``error``, ``system-out`` and ``system-err`` XML elements.

List of supported XML attributes:

* ``classname`` - Python module where reported test was defined.
* ``name`` - name of reported test, mostly name of Python function or Python class.
* ``time`` - total wall time of executed test in seconds.

Example:

.. code:: xml

    <testcase classname="test_dff" name="dff_simple_test" time="0.001">
    </testcase>


.. _junit-attributes-properties:

properties
----------

List of ``property`` XML elements.

No XML attributes.

.. code:: xml

    <properties>
      <property name="cocotb" value="True" />
    </properties>


.. _junit-attributes-property:

property
--------

Reported data by test that cannot be represtented as XML attribute in ``testcase`` XML element.

List of supported XML attributes:

* ``name`` - name of test property.
* ``value`` - value of test property.

List of supported properties:

* ``cocotb`` - mark ``testcase`` as cocotb test. If defined, default value is ``True``.
* ``file`` - path to source file where test was defined.
* ``line`` - line number in file where test was defined.
* ``sim_time_unit`` - simulation time unit like ``ns`` (nanoseconds).
* ``sim_time_duration`` - total simulation time of executed test in ``sim_time_unit``.
* ``sim_time_start`` - simulation time when test started in ``sim_time_unit``.
* ``sim_time_stop`` - simulation time when test finished in ``sim_time_unit``.
* ``sim_time_ratio`` - ratio of wall time to simulation time.
* ``random_seed`` - value of random seed set for test.
* ``attachment`` - file attachment like generated simulation log or waveform files.

Example:

.. code:: xml

    <properties>
      <property name="cocotb" value="True" />
      <property name="random_seed" value="1766926362" />
      <property name="sim_time_unit" value="ns" />
      <property name="sim_time_duration" value="115000.0" />
      <property name="sim_time_ratio" value="139607803.1837916" />
      <property name="attachment" value="sim_build/dff.ghw" />
      <property name="file" value="examples/simple_dff/test_dff.py" />
      <property name="line" value="17" />
      <property name="attachment" value="sim_build/dff.vcd" />
      <property name="attachment" value="sim_build/dff.log" />
    </properties>


.. _junit-attributes-failure:

failure
-------

If present, test failed.

List of supported XML attributes:

* ``message`` - message of raised exception.
* ``type`` - (optional) type of raised exception like ``AssertionError``.

The text part of ``failure`` XML element will contain traceback of raised exception.

Example:

.. code:: xml

    <failure message="value must be equal 5" type="AssertionError">Traceback (most recent call last):
      File "examples/simple_dff/test_dff.py", line 49, in dff_simple_test_failed
        assert value == 5, "value must be equal to 5"
    AssertionError: value must be equal to 5
    assert 3 == 5
    </failure>


.. _junit-attributes-skipped:

skipped
-------

If present, test was skipped.

List of supported XML attributes:

* ``message`` - (optional) reason why test was skipped.

Example:

.. code:: xml

    <skipped message="Test was skipped" />


.. _junit-attributes-error:

error
-----

If present, test finished with an unexpected error.

List of supported XML attributes:

* ``message`` - message of raised exception or error message.
* ``type`` - (optional) type of raised exception like ``RuntimeError``.

The optional text part of ``failure`` XML element will contain traceback of raised exception.


.. _junit-attributes-system-out:

system-out
----------

Optional. It may contain captured standard output of test and file attachments.

No XML attributes.

Example:

.. code:: xml

    <system-out>[[ATTACHMENT|sim_build/dff.ghw]]
    [[ATTACHMENT|sim_build/dff.log]]
    </system-out>


.. _junit-attributes-system-err:

system-err
----------

Optional. It may contain captured standard error of test.

No XML attributes.

Example:

.. code:: xml

    <system-err>Test failed with COCOTB_RANDOM_SEED=1766926362
    </system-err>


.. _junit-examples:

Examples
========

An example of XML with 3 reported tests where 1 test was skipped and another test failed:

.. code:: xml

    <?xml version='1.0' encoding='utf-8'?>
    <testsuites name="cocotb tests">
      <testsuite name="test_dff" errors="0" failures="1" skipped="1" tests="3" time="0.001" timestamp="2025-12-28T12:52:42.287738+00:00" hostname="d9019dc0cfcf">
        <testcase classname="test_dff" name="dff_simple_test" time="0.001">
          <properties>
            <property name="cocotb" value="True" />
            <property name="random_seed" value="1766926362" />
            <property name="sim_time_unit" value="ns" />
            <property name="sim_time_duration" value="115000.0" />
            <property name="sim_time_ratio" value="139607803.1837916" />
            <property name="attachment" value="sim_build/dff.ghw" />
            <property name="file" value="examples/simple_dff/test_dff.py" />
            <property name="line" value="17" />
          </properties>
          <system-out>[[ATTACHMENT|sim_build/dff.ghw]]
    </system-out>
        </testcase>
        <testcase classname="test_dff" name="dff_simple_test_failed" time="0.000">
          <properties>
            <property name="cocotb" value="True" />
            <property name="random_seed" value="1766926362" />
            <property name="sim_time_unit" value="ns" />
            <property name="sim_time_duration" value="0.0" />
            <property name="sim_time_ratio" value="0.0" />
            <property name="attachment" value="sim_build/dff.ghw" />
            <property name="file" value="examples/simple_dff/test_dff.py" />
            <property name="line" value="45" />
          </properties>
          <failure message="value must be equal 5" type="AssertionError">Traceback (most recent call last):
      File "examples/simple_dff/test_dff.py", line 49, in dff_simple_test_failed
        assert value == 5, "value must be equal to 5"
    AssertionError: value must be equal to 5
    assert 3 == 5
    </failure>
          <system-out>[[ATTACHMENT|sim_build/dff.ghw]]
    </system-out>
          <system-err>Test failed with COCOTB_RANDOM_SEED=1766926362
    </system-err>
        </testcase>
        <testcase classname="test_dff" name="dff_simple_test_skipped" time="0.000">
          <properties>
            <property name="cocotb" value="True" />
            <property name="random_seed" value="1766926362" />
            <property name="sim_time_unit" value="ns" />
            <property name="sim_time_duration" value="0.0" />
            <property name="sim_time_ratio" value="0.0" />
            <property name="attachment" value="sim_build/dff.ghw" />
            <property name="file" value="examples/simple_dff/test_dff.py" />
            <property name="line" value="52" />
          </properties>
          <skipped message="Test was skipped" />
          <system-out>[[ATTACHMENT|sim_build/dff.ghw]]
    </system-out>
        </testcase>
      </testsuite>
    </testsuites>


.. _Jenkins xUnit schema version 2: https://github.com/jenkinsci/xunit-plugin/blob/xunit-2.4.0/src/main/resources/org/jenkinsci/plugins/xunit/types/model/xsd/junit-10.xsd
