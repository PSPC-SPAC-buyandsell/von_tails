von_tails
=========
As part of the technology demonstrator project using Hyperledger indy to explore, among other VON network facilities, the use of the distributed ledger with PSPC Supplier Registration Information (SRI), the design specifies anchors to interact with the sovrin distributed ledger as realized through indy-sdk.

The ``von_anchor`` package implements, among other components, issuer and holder-prover VON anchors to handle credentials and proofs. Credential issue and proof creation on revocable credentials entail the use of immutable tails files, which issuers create and holder-provers require.

To facilitate exchange of tails files, the ``von_tails`` package provides a reference implementation of a dedicated tails file service external to the anchors and available through a connection layer such as VON-X.

Documentation
=============
An additional document in this package at `doc/von_tails.doc` includes instructions for installation and operation of ``von_tails``.
