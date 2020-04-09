*******************
Writing Testbenches
*******************

Handling Errors
===============

It may not be clear when to raise an exception and when to use ``log.error()``.

* Use ``raise`` if the caller called your function in an invalid way, and it doesn't make sense to continue.
* Use ``log.error()`` if the hardware itself is misbehaving, and throwing an error immediately would leave it an invalid state.

Even if you do eventually throw an exception (if you weren't able to do it immediately), you should also ``log.error()`` so that the simulation time of when things went wrong is recorded.

TL;DR: ``log.error()`` is for humans only, ``raise`` is for both humans and code.
