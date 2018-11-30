Installation and Configuration
******************************

This section outlines the installation process of the tails file server and synchronization scripts.

Download Project
==============================

To download the project to a host, the operator issues:

.. code-block:: bash

    $ git clone https://github.com/PSPC-SPAC-buyandsell/von_tails.git

at the command prompt. This creates a ``von_tails`` installation directory in place with the software for the tails file server and syncronization scripts.

Build Tails File Server
==============================

Building the tails file server composes a docker container locally, listening on the port that environment variable ``HOST_PORT_VON_TAILS`` specifies (default 8808).

From the ``von_tails`` installation directory, the operator issues at the prompt:

.. code-block:: bash

    $ cd docker
    $ ./manage build

to create the docker image standing up the tails file server.

.. _deploy:

Deploy Source and Create Log Directory
======================================

The operator copies the ``src/sync`` directory from the ``von_tails`` installation directory to the issuer and holder-prover anchor hosts, to a location where ``pipenv`` will pick up the anchor's virtual environment. The operator creates a directory for logs if one is not already present. For example,

.. code-block:: bash

    $ cd /home/operator
    $ mkdir -p von_tails
    $ cd von_tails
    $ scp operator@192.168.56.119:./von_tails/sync .
    $ mkdir -p log

could deploy the synchronization scripts from a tails file server host to an anchor host running the ancho, with all components on all hosts running as user ``operator``.

Prepare Virtual Environment
===========================

On the issuer and holder-prover anchor hosts, the operator ensures that the ``pipenv`` virtual environemtn includes required packages. For example,

.. code-block:: bash

    $ cd /home/operator/von_tails
    $ pipenv install -r sync/requirements.txt

to apply the requirements if the operator installed the ``sync/`` directory in the ``/home/operator/von_tails/sync/`` location as per :ref:`deploy`.

.. _integrate_cron:

Integrate with cron
===================

The operator then updates the cron configuration on each host to engage the ``src/sync/multisync.py`` script every minute, directing it to fire a synchronization operation to the frequency desired (e.g., 20 times per minute or every 3 seconds) and specifying the log location.

A sample cron configuration record for an issuer follows:

.. code-block:: bash

    * * * * * /bin/bash -l -c 'export PIPENV_MAX_DEPTH=16; cd /home/operator/von_tails/sync; pipenv run python multisync.py 20 /home/operator/.indy_client/tails 192.168.56.119 8808 issuer >> /home/operator/von_tails/log/anchor-sync.$(date +\%Y-\%m-\%d).log 2>&1'

and for a holder-prover:

.. code-block:: bash

    * * * * * /bin/bash -l -c 'export PIPENV_MAX_DEPTH=16; cd /home/operator/von_tails/sync; pipenv run python multisync.py 20 /home/operator/.indy_client/tails 192.168.56.119 8808 prover >> /home/operator/von_tails/log/anchor-sync.$(date +\%Y-\%m-\%d).log 2>&1'

where both direct logs to rotating file dated daily.
