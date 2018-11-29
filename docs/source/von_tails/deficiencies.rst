Deficiencies
************************

The project is a reference implementation of an external tails file server. Its current state is provisional, with several candidate areas for future development.

Server Security
====================================

There is no control over what entities can upload to the tails file server, on revocation registries built on what credential definition identifiers nor what issuer DIDs. While tails files are public, a denial of service attack could masquerade as an issuer and upload authoritative-looking bogus tails files to the server. Issuers then would not be able to upload legitimate tails files on the same revocation registry identifiers. Holder-provers would download and use these bad tails files, impeding the proof creation process.

In addition, although the synchronization scripts do not engage it, the tails file server offers a tails file deletion API. This API may present a denial of service attack until issuer synchronization scripts engage and re-upload local-only tails files. If an attacker invokes the deletion API continuously, the attack would tie up resources on the issuer anchor host and make downloads to the holder-prover anchor host unreliable.

Synchronization Script Granularity
====================================

At present, synchronization scripts operate on the entire tails directory structure. Not all holder-provers may be interested in tails file updates from all issuers using a tails file server.

Unit Tests
====================================

At present, there are no formal unit tests included. A full test suite should engage all tails server API calls to ensure correct processing in all possible tails directory states.
