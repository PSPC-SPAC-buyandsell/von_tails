Design Notes
******************************

This section provides design notes on the content of the ``von_tails`` package.

Components
==============================

The package includes a server component and scripts for client use.

Server
++++++++++++++++++++++++++++++

The server side includes a containerized tails file server, implemented in python via Sanic.

Client Scripts
++++++++++++++++++++++++++++++

The synchronization scripts ``src/sync/sync.py`` and ``src/sync/multisync.py`` synchronize tails directories on the anchor host against a remote tails file server. Script ``src/sync/sync.py`` performs one iteration of the synchronization process; ``src/sync/multisync.py`` performs several iterations of the synchronization process, spaces evenly over a single minute. These scripts allow client profiles of issuer or prover: issuers upload to the tails server; provers download from the tails server.

In the case where an audit reveals suspect content, an administrative deletion script ``src/admin/delete.py`` provides a means to delete such via the RESTful API. Any such deletion could follow equally well through local file system operations, but using the RESTful API produces corresponding tails server logs.

Directory Structure
==============================

This section outlines the directory structure in use on the tails file server and clients.

.. image:: https://raw.githubusercontent.com/PSPC-SPAC-buyandsell/von_tails/master/docs/source/pic/dirs.png
    :align: center
    :alt: Directory Structure

Application: Deploying to Container
++++++++++++++++++++++++++++++++++++++++++++++++++

The server application builds on the (python) Sanic framework, mapping URLs to source code in ``/src/app/views.py``.

The application serves tails files from the ``src/tails`` tree, split by credential definition identifier and linked by revocation registry identifier.

Application logs append to the log in ``src/app/log/von_tails.log``.

Client Scripts and Configuration Files: Deployment
++++++++++++++++++++++++++++++++++++++++++++++++++

The ``src/sync/sync.py`` and ``src/sync/multisync.py`` scripts deploy, with configuration file ``/src/sync/config/issuer.ini`` or ``/src/sync/config/prover.ini``, to the host running issuer or holder-prover VON anchors respectively, for invocation via cron.

The ``src/admin/delete.py`` script deploys, with configuration file ``/src/admin/config/admin.ini``, to the tails server site, for invocation on the operating system shell as needed.


Server Design Notes
==============================

This section outlines the tails server image build and container start processes, and introduces its RESTful API.

Build and Start
++++++++++++++++++++++++++++++

In building the tails server container, the ``docker/.manage`` script installs a virtual environment with sanic and ``von_anchor``, then copies all code and configuration constituting the tails server. The build process replaces values where they appear as environment variables (e.g.,  ``${INDY_POOL_NAME}``) in the deployment's genesis transaction and tails server configuration files. The values for these variables come from the ``docker/docker-compose.yml`` file, or, by default, from the build environment.

Container Start
++++++++++++++++++++++++++++++

Upon starting, the tails server container invokes the ``von_anchor_setnym`` script from the virtual environment to register the tails server anchor on the ledger if need be; its configuration comes from the ``src/app/config/config.ini`` file and so it is important that the build arguments be correct in the ``docker/docker-compose.yml`` file before building the image.

Then, the entry point script starts the sanic server process implementing the tails server.

Server Application Programming Interfaces
+++++++++++++++++++++++++++++++++++++++++

The table outlines the API calls that the tails server implements.

.. table:: Tails Server RESTful API

    +---------------------+-----------------------------------+-----------------------------------+----------------------------------------------------------------------------+------------------------------------------+
    | Call                | Method + URL Pattern              | Parameter Values                  | Notes                                                                      | Return Content                           |
    +=====================+===================================+===================================+============================================================================+==========================================+
    | Get anchor DID      | GET /did                          |                                   |                                                                            | Tails server anchor DID, as text         |
    +---------------------+-----------------------------------+-----------------------------------+----------------------------------------------------------------------------+------------------------------------------+
    | Post new tails file | POST /tails/<rr_id>/<epoch>       | Revocation registry identifier,   | Attach (multipart/form-data) files with tails named for tails hash,        | Empty string                             |
    |                     |                                   | epoch time                        | signature over <epoch>||<tails> named ``signature``                        |                                          |
    +---------------------+-----------------------------------+-----------------------------------+----------------------------------------------------------------------------+------------------------------------------+
    | Get tails file      | GET /tails/<rr_id>                | Revocation registry identifier    |                                                                            | (Binary) tails file named for tails hash |
    +---------------------+-----------------------------------+-----------------------------------+----------------------------------------------------------------------------+------------------------------------------+
    | List tails files    | GET /tails/list/<ident>           | ``all``                           | Lists all revocation registry identifiers for which server has tails files | JSON array of                            |
    |                     |                                   +-----------------------------------+----------------------------------------------------------------------------+ revocation registry                      |
    |                     |                                   | Revocation registry identifier    | Lists revocation regisry identifier only if server has its tails file      | identifiers                              |
    |                     |                                   +-----------------------------------+----------------------------------------------------------------------------+                                          |
    |                     |                                   | Credential definition identifier  | Lists revocation registry identifiers for which server has tails files     |                                          |
    |                     |                                   +-----------------------------------+----------------------------------------------------------------------------+                                          |
    |                     |                                   | Issuer DID                        | Lists revocation registry identifiers for which server has tails files     |                                          |
    +---------------------+-----------------------------------+-----------------------------------+----------------------------------------------------------------------------+------------------------------------------+
    | Delete tails files  | DELETE /tails/del/<ident>/<epoch> | ``all``, epoch time               | Attach signature over <epoch>||<ident> named ``signature``;                | Empty string                             |
    |                     |                                   | epoch time                        | deletes all tails content                                                  |                                          |
    |                     |                                   +-----------------------------------+----------------------------------------------------------------------------+                                          |
    |                     |                                   | Issuer DID,                       | Attach signature over <epoch>||<ident> named ``signature``;                |                                          |
    |                     |                                   | epoch time                        | deletes all tails content from specified issuer if present                 |                                          |
    |                     |                                   +-----------------------------------+----------------------------------------------------------------------------+                                          |
    |                     |                                   | Credential definition identifier, | Attach signature over <epoch>||<ident> named ``signature``;                |                                          |
    |                     |                                   | epoch time                        | deletes all tails content for specified credential definition if present   |                                          |
    |                     |                                   +-----------------------------------+----------------------------------------------------------------------------+                                          |
    |                     |                                   | Revocation registry identifier,   | Attach signature over <epoch>||<ident> named ``signature``;                |                                          |
    |                     |                                   | epoch time                        | deletes tails content for specified revocation registry if present         |                                          |
    +---------------------+-----------------------------------+-----------------------------------+----------------------------------------------------------------------------+------------------------------------------+

Data Flow
==============================

The diagram introduces the data flow of typical operations; further discussion elaborates.

.. image:: https://raw.githubusercontent.com/PSPC-SPAC-buyandsell/von_tails/master/docs/source/pic/flow.png
    :align: center
    :alt: Tails Synchronization Sequence

The sequence begins when the actuator prompts the issuer anchor (via its service wrapper API) to issue a new revocable credential, but the issuer must create a new revocation registry.

In the process of issuing the credential, the issuer creates the revocation registry, which generates a corresponding tails file and writes it to local storage. The issuer returns the credential to the actuator via the anchor's service wrapper API; the credential includes a revocation registry identifier.

The actuator polls the holder-prover anchor (via its service wrapper API) periodically for its known tails files by revocation registry identifier, looping until the list includes the one that the new credential specifies.

Running frequently over cron, the synchronization script on the issuer anchor's server polls locally and remotely for tails files, and discovers the new local tails file. The process uploads the file to the remote tails file server.

Meanwhile, also running over cron, the synchronization script on the holder-prover anchor's server polls locally and remotely for tails files. Once the new tails file appears on the tails file server, the synchronization process downloads it to the holder-prover anchor's local storage.

The actuator, polling the holder-prover for its tails files by revocation registry identifier, gets a list indicating the availability of the tails file to the holder-prover anchor. The actuator calls the holder-prover, via its service wrapper API, to store the credential. The anchor stores the credential in its wallet (at this point, not having the corresponding tails file available would raise an exception).

At a future time, the actuator prompts the holder-prover anchor, via its service wrapper API, for proof involving the credential. The anchor uses the tails file in creating the non-revocation component of the proof.

Tails File Vetting
++++++++++++++++++++++++++++++

The tails server vets tails file content as issuers post it, and administrative deletion requests. The tails server does not vet holder-prover requests for content: tails files are public.

The diagram outlines the vetting that the tails server performs prior to accepting requests to add or remove content; further discussion elaborates.

.. image:: https://raw.githubusercontent.com/PSPC-SPAC-buyandsell/von_tails/master/docs/source/pic/vet.png
    :align: center
    :alt: Tails Server Vetting

Vetting Issuer Uploads
------------------------------

The tails server checks that the revocation registry identifier in the URL is of reasonable construction, and that the epoch in the URL is within acceptable clock skew as per server configuration (default 300 seconds). In this way the epoch acts as a salt to avoid replays. Then the server checks the attachments: the tails file name must look like a tails file hash, and both the revocation registry identifier and tails hash must represent new content. It validates the signature attachment, and checks that its signer DID matches the one inscribed in revocation registry identifier. In this way the tails server ensures that only the author of a tails file can upload it. Finally, the tails server VON anchor consults the ledger to get the definition for the revocation registry, and ensures that its tails hash is correct for its posted file name. Only then does it accept the new tails file for distribution to clients acting as holder-provers.

Vetting Deletion Requests
------------------------------

The tails server checks that the epoch in the URL is within acceptable clock skew as per server configuration (default 300 seconds). The server reconstructs the signed content and checks the signature attachment; it checks that its signer DID matches that of the tails server VON anchor itself. Only then does it perform the request to delete tails content that the request identifies.
