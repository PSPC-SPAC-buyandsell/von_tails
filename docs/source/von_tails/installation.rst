Installation and Configuration
******************************

This section outlines the installation process of the tails file server and synchronization scripts.

Download Project
==============================

To download the project to a host, the operator issues:

.. code-block:: bash

    $ git clone https://github.com/PSPC-SPAC-buyandsell/von_tails.git

at the command prompt. This creates a ``von_tails`` installation directory in place with the software for the tails file server and syncronization scripts.

Check Default Server Configuration
==================================

The operator opens file ``src/app/config/config.ini`` from the ``von_tails`` installation directory, adjusting values as need be to fit the environment:

* maximum tails file clock skew allowance, in seconds
* trustee anchor seed and wallet particulars

before saving the file. 

Build Tails File Server
==============================

Building the tails file server composes a docker container locally, listening on the port that environment variable ``${HOST_PORT_VON_TAILS}`` specifies (default 8808).

From the ``von_tails`` installation directory, the operator issues at the prompt:

.. code-block:: bash

    $ cd docker
    $ ./manage build

to create the docker image standing up the tails file server. The sequence above assumes a current installation of ``von_base`` in the operator's home directory.

.. _deploy:

Tails Client Deployment and Configuration
=========================================

This section specifies deployment and configuration for clients of the tails server.

Prepare Client Directory Structure
++++++++++++++++++++++++++++++++++

The operator creates directories to hold scripts, logs, and configuration on issuer and holder-prover anchor hosts of interest. For example, the operator could issue:

.. code-block:: bash

    $ cd /home/operator
    $ mkdir -p von_tails/config
    $ mkdir -p von_tails/log

to prepare the directory structure with all components to run as ``operator`` on the host.

.. _deploy-src-reqs:

Deploy Source and Requirements Specifications
+++++++++++++++++++++++++++++++++++++++++++++

The operator copies the ``*.py`` scripts and ``requirements.txt`` files from the ``src/sync`` directory of the ``von_tails`` installation directory to the issuer and holder-prover anchor hosts, to a location where ``pipenv`` will pick up the anchor's virtual environment (see :ref:`venv`). For example, on a host running a VON anchor to synchronize, the operator could issue:

.. code-block:: bash

    $ cd /home/operator
    $ cd von_tails
    $ scp operator@192.168.56.119:./von_tails/src/sync/\*.{py,txt} .

to deploy source and requirements specification files.

Adjust Tails Client Configuration
+++++++++++++++++++++++++++++++++

This section details the configuration process for tails clients.

Issuer Anchor Host
------------------

In particular, on a host running an issuer VON anchor, the operator issues:

.. code-block:: bash

    $ cd /home/operator
    $ cd von_tails/config
    $ scp operator@192.168.56.119:./von_tails/src/sync/config/issuer.ini .

The operator edits the configuration file to fit the operating environment as per :ref:`sync-config`.

At a minimum, the operator must supply bona fide values for:

* the genesis transaction path to bootstrap the indy pool.
* the issuer VON anchor seed and wallet particulars.

Holder-Prover Anchor Host
-------------------------

On a host running a holder-prover VON anchor, the operator issues instead:

.. code-block:: bash

    $ cd /home/operator
    $ cd von_tails/config
    $ scp operator@192.168.56.119:./von_tails/src/sync/config/prover.ini .

The operator edits the configuration file to fit the operating environment as per :ref:`sync-config`.

At a minimum, the operator must supply a bona fide value for the holder-prover VON anchor's tails directory.

Tails Server Host
-----------------

On the tails server host, the operator locates and edit configuration file ``von_tails/src/admin/config/admin.ini`` to fit the operating environment as per :ref:`sync-config`; its VON anchor is the tails server anchor.

At a minimum, the operator must supply a bona fide value for the genesis transaction path to bootstrap the indy pool.

.. _venv:

Prepare Virtual Environment
===========================

This section outlines the process preparing the virtual environment on tails client hosts.

Issuer and Holder-Prover Hosts
++++++++++++++++++++++++++++++

On the issuer and holder-prover tails client hosts, the operator ensures that the virtual environment includes required packages as the ``requirements.txt`` copied as per :ref:`deploy-src-reqs` specifies. For example, the sequence:

.. code-block:: bash

    $ cd /home/operator/von_tails
    $ pipenv install -r requirements.txt

could prepare the virtual environment for synchronization if the operator installed the ``src/sync/`` directory in the ``/home/operator/von_tails/`` location as per :ref:`deploy`.

Tails Server Host
+++++++++++++++++

On the tails server host, the operator ensures that the virtual environment includes required packages as ``src/admin/requirements.txt`` specifies in the ``von_tails`` distribution. For example, the sequence:

.. code-block:: bash

    $ cd /home/operator
    $ cd von_tails/src/admin
    $ pipenv install -r requirements.txt

could prepare the virtual environment for the administrative deletion script for a tails server with VON tails deployed to directory ``/home/operator/von_tails``.

.. _integrate-cron:

Integrate with cron
===================

On the issuer and holder-prover anchor tails client hosts, the operator updates the cron configuration on each host to engage the ``src/multisync.py`` script every minute, directing it to fire a synchronization operation to the frequency desired (e.g., 20 times per minute or every 3 seconds) and specifying the configuration file.

A sample cron configuration record for an issuer follows:

.. code-block:: bash

    * * * * * /bin/bash -l -c 'export PIPENV_MAX_DEPTH=16; cd /home/operator/von_tails; pipenv run python multisync.py 20 /home/operator/von_tails/config/issuer.ini >> /home/operator/von_tails/log/anchor-sync.$(date +\%Y-\%m-\%d).log 2>&1'

and for a holder-prover:

.. code-block:: bash

    * * * * * /bin/bash -l -c 'export PIPENV_MAX_DEPTH=16; cd /home/operator/von_tails; pipenv run python multisync.py 20 /home/operator/von_tails/config/prover.ini >> /home/operator/von_tails/log/anchor-sync.$(date +\%Y-\%m-\%d).log 2>&1'

where both direct logs to daily rotating file.
