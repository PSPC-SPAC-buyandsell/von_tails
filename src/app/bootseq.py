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

from app.cache import MEM_CACHE
from von_anchor import NominalAnchor, TrusteeAnchor
from von_anchor.error import ExtantWallet
from von_anchor.frill import do_wait
from von_anchor.indytween import Role
from von_anchor.nodepool import NodePool
from von_anchor.util import AnchorData, NodePoolData
from von_anchor.wallet import Wallet


LOGGER = logging.getLogger(__name__)


def boot() -> None:
    """
    Boot the service: instantiate tails server anchor
    """

    config = do_wait(MEM_CACHE.get('config'))

    pool_data = NodePoolData(
        config['Node Pool']['name'],
        config['Node Pool'].get('genesis.txn.path', None) or None)  # nudge empty value from '' to None
    pool = NodePool(pool_data.name, pool_data.genesis_txn_path)
    do_wait(pool.open())
    assert pool.handle
    do_wait(MEM_CACHE.set('pool', pool))

    # instantiate tails server anchor
    tsan_data = AnchorData(
        Role.USER,
        config['VON Anchor'].get('seed', None) or None,
        config['VON Anchor']['wallet.name'],
        config['VON Anchor'].get('wallet.type', None) or None,
        config['VON Anchor'].get('wallet.key', None) or None)

    wallet = Wallet(
        tsan_data.wallet_name,
        tsan_data.wallet_type,
        None,
        {'key': tsan_data.wallet_key} if tsan_data.wallet_key else None)

    if tsan_data.seed:
        try:
            do_wait(wallet.create(tsan_data.seed))
            LOGGER.info('Created wallet {}'.format(tsan_data.wallet_name))
        except ExtantWallet:
            LOGGER.warning('Wallet {} already exists: remove seed from config file'.format(tsan_data.wallet_name))

    do_wait(wallet.open())
    tsan = NominalAnchor(wallet, pool)
    do_wait(tsan.open())
    assert tsan.did
    if not json.loads(do_wait(tsan.get_nym())):
        LOGGER.error('Anchor {} has no cryptonym on the ledger'.format(tsan_data.wallet_name))

    do_wait(MEM_CACHE.set('tsan', tsan))
