Design Notes
******************************

This section provides design notes on the content of the ``von_tails`` package.

Components
==============================

The package includes a server component and synchronization scripts.

Server
++++++++++++++++++++++++++++++

The server side includes a containerized tails file server, implemented in python via Sanic.

Synchronization Scripts
++++++++++++++++++++++++++++++

The synchronization scripts ``src/sync.py`` and ``src/multisync.py`` synchronize tails directories on the anchor host against a remote tails file server. Script ``src/sync.py`` performs one iteration of the synchronization process; ``src/multisync.py`` performs several iterations of the synchronization process, spaces evenly over a single minute.

The high level design does not specify the client (actuator) to prompt VON anchor operations; it could be a configuration item for a Web application or it could be a custom application prodding one or more anchors via their respective wrapper APIs. The ``test/test_anchors.py`` test harness of the VON Anchor package offers a (crude) sample actuator.

Directory Structure
==============================

This section outlines the directory structure in use on the tails file server.

.. image:: https://raw.githubusercontent.com/PSPC-SPAC-buyandsell/von_tails/master/docs/source/pic/dirs.png
    :align: center
    :alt: Directory Structure

Application: Deploying to Container
++++++++++++++++++++++++++++++++++++++++++++++++++

The server application builds on the (python) Sanic framework, mapping URLs to source code in ``/src/app/views.py``.

The application serves tails files from the ``src/tails`` tree, split by credential definition identifier and linked by revocation registry identifier.

Application logs append to the log in ``src/applog/von_tails.log``.

Synchronization Scripts: Deploying to Anchor Hosts
++++++++++++++++++++++++++++++++++++++++++++++++++

The ``src/sync.py`` and ``src/multisync.py`` scripts deploy to the host running issuer or holder-prover hosts, for invocation via cron.

Server Application Programming Interfaces
=========================================

The table outlines the API calls that the tails server implements.

.. table:: Tails Server RESTful API

    +----------------------+-----------------------------+----------------------------------+----------------------------------------------------------------------------+-----------------------------------------------+
    | Call                 | Method + URL Pattern        | Parameter Value                  | Notes                                                                      | Return Content                                |
    +======================+=============================+==================================+============================================================================+===============================================+
    | Post new tails file  | POST /tails/*<rr_id>*       | Revocation registry identifier   | Attach (multipart/form-data) file named for tails hash                     | Empty string                                  |
    +----------------------+-----------------------------+----------------------------------+----------------------------------------------------------------------------+-----------------------------------------------+
    | Get tails file       | GET /tails/*<rr_id>*        | Revocation registry identifier   |                                                                            | (Binary) tails file named for tails hash      |
    +----------------------+-----------------------------+----------------------------------+----------------------------------------------------------------------------+-----------------------------------------------+
    | List tails files     | GET /tails/list/*<ident>*   | ``all``                          | Lists all revocation registry identifiers for which server has tails files | JSON array of revocation registry identifiers |
    |                      |                             +----------------------------------+----------------------------------------------------------------------------+                                               |
    |                      |                             | Revocation registry identifier   | Lists revocation regisry identifier only if server has its tails file      |                                               |
    |                      |                             +----------------------------------+----------------------------------------------------------------------------+                                               |
    |                      |                             | Credential definition identifier | Lists revocation registry identifiers for which server has tails files     |                                               |
    |                      |                             +----------------------------------+----------------------------------------------------------------------------+                                               |
    |                      |                             | Issuer DID                       | Lists revocation registry identifiers for which server has tails files     |                                               |
    +----------------------+-----------------------------+----------------------------------+----------------------------------------------------------------------------+-----------------------------------------------+
    | Delete tails files   | DELETE /tails/del/*<ident>* | ``all``                          | Deletes all tails files                                                    | Empty string                                  |
    |                      |                             +----------------------------------+----------------------------------------------------------------------------+                                               |
    |                      |                             | Revocation registry identifier   | Deletes tails file only if server has one corresponding                    |                                               |
    |                      |                             +----------------------------------+----------------------------------------------------------------------------+                                               |
    |                      |                             | Credential definition identifier | Deletes corresponding tails files                                          |                                               |
    |                      |                             +----------------------------------+----------------------------------------------------------------------------+                                               |
    |                      |                             | Issuer DID                       | Deletes corresponding tails files                                          |                                               |
    +----------------------+-----------------------------+----------------------------------+----------------------------------------------------------------------------+-----------------------------------------------+

Data Flow
==============================

The diagram introduces the data flow of the design; further discussion elaborates.

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
