Operation
******************************

This section discusses the operation of the tails file server and synchronization scripts.

Tails Server
==============================

This section outlines the startup and shutdown of the tails server.

Stop and Start
------------------------------

To stop and start the tails file server in the foreground, the operator changes to the ``von_tails`` installation directory and issues

.. code-block:: bash

    $ cd docker
    $ ./manage stop
    $ ./manage start

at the prompt. The execution occupies the terminal window; the tails file server is ready when the operation outputs a record noting that Sanic is "Goin' Fast" on the configured port.

The startup process always begins from scratch on ``manage start``, removing any extant containers from prior operations.

To start the tails file server in the background, the operator may issue 

.. code-block:: bash

    $ ./manage bg

instead, which starts the tails file server (or resumes operation from any existing containers) in the shell's background.

The operator may follow the tails file server container's docker logs via

.. code-block:: bash

    $ docker logs -f <docker_von_tails_1>

where ``<docker_von_tails_1>`` represents the agent container (not image) of interest.

Container Shutdown and Removal
------------------------------

To stop the tails server container, the operator changes to the ``von_tails`` installation directory and issues

.. code-block:: bash

    $ cd docker
    $ ./manage stop

at the prompt. Alternatively, if the docker containers are operating in the terminal's foreground, the operator may simply issue control-C and wait for graceful shutdown.

To stop and remove all containers, the operator may issue

.. code-block:: bash

    $ ./manage rm

at the prompt.

Synchronization Scripts
------------------------------

Script ``src/sync.py`` performs one iteration of the synchronization process. An operator may call this script for a one-time manual synchronization operation. Its command line arguments represent:

- the topmost tails directory for the VON anchor
- the tails server hostname or IP address
- the tails server port
- the synchronization role:

  - ``issuer`` to upload local-only tails files from within the tails directory to the server
  - ``prover`` to download remote-only tails files from the server to the tails directory.

Script ``src/multisync.py`` performs several iterations of the synchronization process, spaced evenly over a single minute: the number of such iterations appears as the first parameter, preceding those that it passes to the src/sync.py script.

A new iteration of the synchronization process only starts if one is not already running – typical operation will not overlap iterations.

This script's intended use is integration via cron, as per :ref:`integrate_cron`.
