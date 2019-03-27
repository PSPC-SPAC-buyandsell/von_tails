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


import logging

from os import sys
from time import time
from urllib.parse import quote

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError

from von_anchor import NominalAnchor
from von_anchor.error import ExtantWallet
from von_anchor.frill import do_wait, inis2dict
from von_anchor.indytween import Role
from von_anchor.nodepool import NodePoolManager
from von_anchor.op import AnchorData, NodePoolData
from von_anchor.wallet import WalletManager


def usage() -> None:
    """
    Print usage message.
    """

    print('\nUsage: delete.py <config-ini> <ident>')
    print()
    print('where:')
    print('    * <config-ini> represents the path to the configuration file, and')
    print('    * <ident> represents:')
    print('      - the literal "all" (no quotes) for no filter,')
    print('      - a schema origin DID,')
    print('      - a credential definition identifier, or')
    print('      - a revocation registy identifier.')
    print()
    print('The operation deletes tails files corresponding to <ident> at the server.')
    print()
    print('The configuration file has sections and entries as follows:')
    print('  * section [Tails Server]:')
    print('    - host: the hostname or address of the tails server')
    print('    - port: the port on which the tails server listens')
    print('  * section [Node Pool]:')
    print('    - name: the name of the node pool to which the operation applies')
    print('    - genesis.txn.path: the path to the genesis transaction file')
    print('        for the node pool (may omit if pool already exists)')
    print('  * section [VON Anchor], pertaining to the tails server VON anchor:')
    print("    - name: the VON anchor's wallet name")
    print("    - seed: the VON anchor's seed (omit if wallet exists)")
    print('    - wallet.create: (default False) whether to create the')
    print('        tails server VON anchor wallet if it does not exist')
    print("    - wallet.type: (default blank) the VON anchor's wallet type")
    print("    - wallet.access: (default blank) the VON anchor's")
    print('        wallet access credential (password) value.')
    print()


async def get_wallet(tsan_data: AnchorData):
    """
    Get wallet given configuration data for Tails Server Anchor

    :param tsan_data: Tails Server Anchor data
    """

    w_mgr = WalletManager()
    rv = None

    wallet_config = {
        'id': tsan_data.name
    }
    if tsan_data.wallet_type:
        wallet_config['storage_type'] = tsan_data.wallet_type
    if tsan_data.wallet_create:
        if tsan_data.seed:
            wallet_config['seed'] = tsan_data.seed
        try:
            rv = await w_mgr.create(wallet_config, access=tsan_data.wallet_access)
            logging.info('Created wallet %s', tsan_data.name)
        except ExtantWallet:
            rv = await w_mgr.get(wallet_config, access=tsan_data.wallet_access)
            logging.warning(
                'Wallet %s already exists: remove seed and wallet.create from config file',
                tsan_data.name)
    else:
        rv = await w_mgr.get(wallet_config, access=tsan_data.wallet_access)

    return rv


async def admin_delete(ini_path: str, ident: str) -> int:
    """
    Set configuration from file, open node pool and anchor, and request deletion from tails file server
    of tails files that identifier specifies.

    :param ini_path: path to configuration file
    :param ident: identifier to specify in deletion request
    :return: 0 for OK, 1 for failure.
    """

    config = inis2dict(ini_path)
    pool_data = NodePoolData(
        config['Node Pool']['name'],
        config['Node Pool'].get('genesis.txn.path', None) or None)  # nudge empty value from '' to None
    tsan_data = AnchorData(
        Role.USER,
        config['VON Anchor']['name'],
        config['VON Anchor'].get('seed', None) or None,
        None,
        config['VON Anchor'].get('wallet.create', '0').lower() in ['1', 'true', 'yes'],
        config['VON Anchor'].get('wallet.type', None) or None,
        config['VON Anchor'].get('wallet.access', None) or None)

    # Set up node pool ledger config and wallet
    manager = NodePoolManager()
    if pool_data.name not in await manager.list():
        if pool_data.genesis_txn_path:
            await manager.add_config(pool_data.name, pool_data.genesis_txn_path)
        else:
            logging.error(
                'Node pool %s has no ledger configuration but %s specifies no genesis transaction path',
                pool_data.name,
                ini_path)
            return 1

    wallet = await get_wallet(tsan_data)
    async with wallet, (
            manager.get(pool_data.name)) as pool, (
            NominalAnchor(wallet, pool)) as noman:

        host = config['Tails Server']['host']
        port = config['Tails Server']['port']
        epoch = int(time())
        url = 'http://{}:{}/tails/{}/{}'.format(host, port, quote(ident), epoch)
        signature = await noman.sign('{}||{}'.format(epoch, ident))
        try:
            resp = requests.delete(url, data=signature)
            logging.info('DELETE: url %s status %s', url, resp.status_code)
            if resp.status_code != requests.codes.ok:
                return 1
        except RequestsConnectionError:
            logging.error('DELETE connection refused: %s', url)
            return 1


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)-15s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('urllib').setLevel(logging.ERROR)
    logging.getLogger('von_anchor').setLevel(logging.WARNING)
    logging.getLogger('indy').setLevel(logging.CRITICAL)

    if len(sys.argv) != 3:
        usage()
    else:
        do_wait(admin_delete(sys.argv[1], sys.argv[2]))
