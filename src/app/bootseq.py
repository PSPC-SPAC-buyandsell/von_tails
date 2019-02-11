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
from von_anchor.error import AbsentNym, AbsentPool, ExtantWallet
from von_anchor.frill import do_wait
from von_anchor.indytween import Role
from von_anchor.nodepool import NodePool, NodePoolManager
from von_anchor.util import AnchorData, NodePoolData
from von_anchor.wallet import Wallet


LOGGER = logging.getLogger(__name__)


def boot() -> None:
    """
    Boot the service: instantiate tails server anchor. Raise AbsentPool if node pool ledger configuration
    neither present nor sufficiently specified; raise AbsentNym if tails server anchor nym is not on the ledger.
    """

    config = do_wait(MEM_CACHE.get('config'))

    # setup pool and wallet
    pool_data = NodePoolData(
        config['Node Pool']['name'],
        config['Node Pool'].get('genesis.txn.path', None) or None)  # nudge empty value from '' to None
    manager = NodePoolManager()
    if pool_data.name not in do_wait(manager.list()):
        if pool_data.genesis_txn_path:
            manager.add_config(pool_data.name, pool_data.genesis_txn_path)
        else:
            LOGGER.debug(   
                'Node pool %s has no ledger configuration but %s specifies no genesis txn path',
                do_wait(MEM_CACHE.get('config.ini')),
                pool_data.name)
            raise AbsentPool('Node pool {} has no ledger configuration but {} specifies no genesis txn path'.format(
                pool_data.name))

    pool = manager.get(pool_data.name)
    do_wait(pool.open())
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
            LOGGER.info('Created wallet %s', tsan_data.wallet_name)
        except ExtantWallet:
            LOGGER.warning('Wallet %s already exists: remove seed from config file', tsan_data.wallet_name)

    do_wait(wallet.open())
    tsan = NominalAnchor(wallet, pool)
    do_wait(tsan.open())
    if not json.loads(do_wait(tsan.get_nym())):
        LOGGER.debug('Anchor %s has no cryptonym on ledger %s', tsan_data.wallet_name, pool_data.name)
        raise AbsentNym('Anchor {} has no cryptonym on ledger {}'.format(tsan_data.wallet_name, pool_data.name))

    do_wait(MEM_CACHE.set('tsan', tsan))
