VON Tails
=========

As part of the technology demonstrator project using Hyperledger indy to explore, among other VON network facilities, the use of the distributed ledger with PSPC Supplier Registration Information (SRI), the ``von_anchor`` design specifies anchors to interact with the sovrin distributed ledger as realized through indy-sdk.

The ``von_anchor`` package implements, among other components, issuer and holder-prover VON anchors to handle credentials and proofs. Credential issue and proof creation on revocable credentials entail the use of immutable tails files, which issuers create and holder-provers require.

The process of synchronizing tails file between issuer and holder-prover anchors is beyond the scope of indy-sdk and the VON Anchor project. To facilitate exchange of tails files, the ``von_tails`` package provides a reference implementation of a tails file server external to the anchors using them. In addition, it provides synchronization scripts to upload tails files from issuers and download to holder-provers as they become available.

Documentation
=============

For documentation regarding installation and operation, please visit https://von-tails.readthedocs.io/en/latest/. For documentation on the ``von_anchor`` project, please consult https://von-anchor.readthedocs.io/en/latest/.
