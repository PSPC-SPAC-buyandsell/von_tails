"""
Copyright 2017-2019 Government of Canada - Public Services and Procurement Canada - buyandsell.gc.ca

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import json
import logging

from os.path import dirname, join, realpath

from von_anchor import NominalAnchor, TrusteeAnchor
from von_anchor.frill import do_wait
from von_anchor.nodepool import NodePool
from von_anchor.wallet import Wallet

from app.cache import MEM_CACHE


LOGGER = logging.getLogger(__name__)


def boot() -> None:
    """
    Boot the service: instantiate tails server anchor
    """

    config = do_wait(MEM_CACHE.get('config'))
    pool_name = config['Node Pool']['name']
    genesis_txn_path = config['Node Pool']['genesis.txn.path']

    pool = NodePool(pool_name, genesis_txn_path)
    do_wait(pool.open())
    assert pool.handle
    do_wait(MEM_CACHE.set('pool', pool))

    # instantiate tails server anchor
    ts_seed = config['VON Anchor']['seed']
    ts_wallet_name = config['VON Anchor']['wallet.name']
    ts_wallet_type = config['VON Anchor'].get('wallet.type', None) or None  # nudge empty value from '' to None
    ts_wallet_key = config['VON Anchor'].get('wallet.key', None) or None
    tsan = NominalAnchor(
        do_wait(Wallet(
            ts_seed,
            ts_wallet_name,
            ts_wallet_type,
            None,
            {'key': ts_wallet_key} if ts_wallet_key else None).create()),
        pool)
    do_wait(tsan.open())
    assert tsan.did

    do_wait(MEM_CACHE.set('tsan', tsan))
