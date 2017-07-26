========================================================
pyOpenSSL -- A Python wrapper around the OpenSSL library
========================================================

.. image:: https://readthedocs.org/projects/pyopenssl/badge/?version=stable
   :target: https://pyopenssl.org/en/stable/
   :alt: Stable Docs

.. image:: https://travis-ci.org/pyca/pyopenssl.svg?branch=master
   :target: https://travis-ci.org/pyca/pyopenssl
   :alt: Build status

.. image:: https://codecov.io/github/pyca/pyopenssl/branch/master/graph/badge.svg
   :target: https://codecov.io/github/pyca/pyopenssl
   :alt: Test coverage


High-level wrapper around a subset of the OpenSSL library.  Includes

* ``SSL.Connection`` objects, wrapping the methods of Python's portable sockets
* Callbacks written in Python
* Extensive error-handling mechanism, mirroring OpenSSL's error codes

... and much more.

You can find more information in the documentation_.
Development takes place on GitHub_.


Discussion
==========

If you run into bugs, you can file them in our `issue tracker`_.

We maintain a cryptography-dev_ mailing list for both user and development discussions.

You can also join ``#cryptography-dev`` on Freenode to ask questions or get involved.


.. _documentation: https://pyopenssl.org/
.. _`issue tracker`: https://github.com/pyca/pyopenssl/issues
.. _cryptography-dev: https://mail.python.org/mailman/listinfo/cryptography-dev
.. _GitHub: https://github.com/pyca/pyopenssl


Release Information
===================

17.2.0 (2017-07-20)
-------------------


Backward-incompatible changes:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*none*


Deprecations:
^^^^^^^^^^^^^

- Deprecated ``OpenSSL.rand`` - callers should use ``os.urandom()`` instead.
  `#658 <https://github.com/pyca/pyopenssl/pull/658>`_


Changes:
^^^^^^^^

- Fixed a bug causing ``Context.set_default_verify_paths()`` to not work with cryptography ``manylinux1`` wheels on Python 3.x.
  `#665 <https://github.com/pyca/pyopenssl/pull/665>`_
- Fixed a crash with (EC)DSA signatures in some cases.
  `#670 <https://github.com/pyca/pyopenssl/pull/670>`_

`Full changelog <https://pyopenssl.org/en/stable/changelog.html>`_.



