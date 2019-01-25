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
import logging
import re

from os import makedirs, sys
from os.path import basename, isdir, join
from time import time
from typing import Any, Callable
from urllib.parse import quote

import requests
from requests.exceptions import ConnectionError

from von_anchor import NominalAnchor
from von_anchor.error import ExtantWallet
from von_anchor.frill import do_wait, inis2dict
from von_anchor.indytween import Role
from von_anchor.nodepool import NodePool
from von_anchor.tails import Tails
from von_anchor.util import AnchorData, NodePoolData
from von_anchor.wallet import Wallet


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
    print("    - seed: the VON anchor's seed (omit if wallet exists)")
    print("    - wallet.name: the VON anchor's wallet name")
    print("    - wallet.type: (default blank) the VON anchor's wallet type")
    print("    - wallet.key: (default blank) the VON anchor's")
    print('        wallet access credential (password) value.')
    print()


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
            await wallet.create(tsan_data.seed)
            logging.info('Created wallet {}'.format(tsan_data.wallet_name))
        except ExtantWallet:
            logging.warning('Wallet {} already exists: remove seed from configuration file {}'.format(
                tsan_data.wallet_name,
                ini_path))

    async with wallet, (
            NodePool(pool_data.name, pool_data.genesis_txn_path)) as pool, (
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
        except ConnectionError:
            logging.error('DELETE connection refused: %s', url)
            return 1


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)-15s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('urllib').setLevel(logging.ERROR)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('von_anchor').setLevel(logging.WARNING)
    logging.getLogger('indy').setLevel(logging.CRITICAL)

    if len(sys.argv) != 3:
        usage()
    else:
        do_wait(admin_delete(sys.argv[1], sys.argv[2]))
