************************
Unit Tests
************************

The test suite at ``test/test_server.py`` starts the service and exercises the basic synchronization functionality of issuer and prover profiles. It assumes that the operator has built the tails server as per :ref:`build-tails-server`, but that the server is not running.

Prerequisites
========================

Before running the test suite for the first time, the operator issues:

.. code-block:: bash

    $ cd ~/von_tails/test
    $ pipenv install -r requirements.txt

to set requirements in the virtual environment.

Test Operation
========================

To run the test suite, the operator issues:

.. code-block:: bash

    $ cd ~/von_tails/test
    $ pipenv run pytest -s test_server.py

and ensures that the operation completes successfully. The test, at present,

* starts the tails server on its node pool
* sets issuer and prover anchor cryptonyms on the ledger
* creates enough credentials to create 4 local revocation registries on the issuer side
* lists the content of the tails server, ensuring that it is initially empty
* uploads the issuer's local-only tails files
* lists the tails server content to ensure that it matches the issuer's local-only content
* downloads tails server content, using the prover profile
* checks the prover tails directory, to ensure its proper synchronization with the tails server
* administratively deletes all content from the tails server and ensures its removal
* tears down the tails server, node pool, and indy artifacts.
