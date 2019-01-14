Deficiencies
************************

The project is a reference implementation of an external tails file server. Its current state is provisional, with several candidate areas for future development.

Server Security
====================================

At present, the tails server vets issuer uploads by signature against the current time and proof of origin - only its issuer may upload a tails file for a revocation registry; the current time serves as a nonce within configurable clock skew. Similarly, the tails file server vets administrative deletion requests against the current time and proof of origin - only the tails server anchor itself may call for deletion via the RESTful API.

There is no connection security tied to the tails file server; it operates on http. TLS implementation would require a proxy server, integration of X.509 TLS certificate organizational PKI, and/or a DID-auth_ implementation on the tails server itself.

.. _DID-auth: https://github.com/WebOfTrustInfo/rwot6-santabarbara/blob/master/draft-documents/did_auth_draft.md

There is no master access control list to restrict uploads to issuers of interest: at present, any issuer anchor on the ledger may post its tails files to any tails file server.

Synchronization Script Granularity
====================================

At present, the issuer synchronization process selects for tails files corresponding to revocation registries that the issuer anchor built. Operating as a prover profile, synchronization scripts operate on the entire tails directory structure, and download all tails files at the server. Not all holder-provers may be interested in tails file updates from all issuers using a tails file server.

Unit Tests
====================================

At present, there are no formal unit tests included. A full test suite should engage all tails server API calls to ensure correct processing in all possible tails directory states.
