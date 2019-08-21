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

import json
import logging

from von_anchor import NominalAnchor
from von_anchor.error import AbsentNym, AbsentPool, ExtantWallet
from von_anchor.frill import do_wait
from von_anchor.indytween import Role
from von_anchor.nodepool import NodePoolManager
from von_anchor.op import AnchorData, NodePoolData
from von_anchor.wallet import WalletManager

from app.cache import MEM_CACHE


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
    p_mgr = NodePoolManager()
    if pool_data.name not in do_wait(p_mgr.list()):
        if pool_data.genesis_txn_path:
            do_wait(p_mgr.add_config(pool_data.name, pool_data.genesis_txn_path))
        else:
            LOGGER.debug(
                'Node pool %s has no ledger configuration but %s specifies no genesis txn path',
                pool_data.name,
                do_wait(MEM_CACHE.get('config.ini')))
            raise AbsentPool('Node pool {} has no ledger configuration but {} specifies no genesis txn path'.format(
                pool_data.name,
                do_wait(MEM_CACHE.get('config.ini'))))

    pool = p_mgr.get(pool_data.name)
    do_wait(pool.open())
    do_wait(MEM_CACHE.set('pool', pool))

    # instantiate tails server anchor
    tsan_data = AnchorData(
        Role.USER,
        config['VON Anchor']['name'],
        config['VON Anchor'].get('seed', None) or None,
        None,
        config['VON Anchor'].get('wallet.create', '0').lower() in ['1', 'true', 'yes'],
        config['VON Anchor'].get('wallet.type', None) or None,
        config['VON Anchor'].get('wallet.access', None) or None)

    w_mgr = WalletManager()
    wallet = None

    wallet_config = {
        'id': tsan_data.name
    }
    if tsan_data.wallet_type:
        wallet_config['storage_type'] = tsan_data.wallet_type
    if tsan_data.wallet_create:
        if tsan_data.seed:
            wallet_config['seed'] = tsan_data.seed
        try:
            wallet = do_wait(w_mgr.create(wallet_config, access=tsan_data.wallet_access))
            LOGGER.info('Created wallet %s', tsan_data.name)
        except ExtantWallet:
            wallet = w_mgr.get(wallet_config, access=tsan_data.wallet_access)
            LOGGER.warning('Wallet %s already exists: remove seed and wallet.create from config file', tsan_data.name)
    else:
        wallet = w_mgr.get(wallet_config, access=tsan_data.wallet_access)

    do_wait(wallet.open())
    tsan = NominalAnchor(wallet, pool)
    do_wait(tsan.open())
    if not json.loads(do_wait(tsan.get_nym())):
        LOGGER.debug('Anchor %s has no cryptonym on ledger %s', tsan_data.wallet_name, pool_data.name)
        raise AbsentNym('Anchor {} has no cryptonym on ledger {}'.format(tsan_data.wallet_name, pool_data.name))

    do_wait(MEM_CACHE.set('tsan', tsan))
