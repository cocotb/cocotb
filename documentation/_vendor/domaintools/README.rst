Domain Tools
============

This `Sphinx extension`_ provides a tool for easy `sphinx domain`_ creation.

.. _Sphinx extension: http://sphinx-doc.org
.. _sphinx domain: http://sphinx-doc.org/domains.html


Installation
------------

::

    pip install sphinxcontrib-domaintools


Usage
-----

In this example there is created a simple domain for `GNU Make`_::

    from sphinxcontrib.domaintools import custom_domain

    def setup(app):
        app.add_domain(custom_domain('GnuMakeDomain',
            name  = 'make',
            label = "GNU Make", 

            elements = dict(
                target = dict(
                    objname      = "Make Target",
                    indextemplate = "pair: %s; Make Target",
                ),
                var   = dict(
                    objname = "Make Variable",
                    indextemplate = "pair: %s; Make Variable"
                ),
            )))

.. _GNU Make: http://www.gnu.org/software/make/

Complete example you find in `sphinxcontrib.makedomain`_ package.

A more complex example you can find in `sphinxcontrib-cmakedomain`_ package.

.. _sphinxcontrib-cmakedomain: http://bitbucket.org/klorenz/sphinxcontrib-cmakedomain
.. _sphinxcontrib-makedomain: http://bitbucket.org/klorenz/sphinxcontrib-makedomain


Reference
---------

.. py:function:: custom_domain(class_name, name='', label='', elements = {}):

    Create a custom domain.

    For each given element there are created a directive and a role
    for referencing and indexing.

    :param class_name: ClassName of your new domain (e.g. `GnuMakeDomain`)
    :param name      : short name of your domain (part of directives, e.g. `make`)
    :param label     : Long name of your domain (e.g. `GNU Make`)
    :param elements  :
        dictionary of your domain directives/roles

        An element value is a dictionary with following possible entries:

        - `objname` - Long name of the entry, defaults to entry's key

        - `role` - role name, defaults to entry's key

        - `indextemplate` - e.g. ``pair: %s; Make Target``, where %s will be 
          the matched part of your role.  You may leave this empty, defaults 
          to ``pair: %s; <objname>``

        - `parse_node` - a function with signature ``(env, sig, signode)``,
          defaults to `None`.

        - `fields` - A list of fields where parsed fields are mapped to. this
          is passed to Domain as `doc_field_types` parameter.

        - `ref_nodeclass` - class passed as XRefRole's innernodeclass,
          defaults to `None`.


License
-------

New BSD License.


Author
------

`Kay-Uwe (Kiwi) Lorenz <kiwi@franka.dyndns.org>`_ (http://quelltexter.org)
