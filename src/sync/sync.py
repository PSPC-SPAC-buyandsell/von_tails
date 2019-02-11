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
import atexit
import logging
import re

from configparser import ConfigParser
from enum import Enum
from os import makedirs, sys
from os.path import basename, expandvars, isdir, join
from time import time
from typing import Any, Callable
from urllib.parse import quote

import requests
from requests.exceptions import ConnectionError

from indy.error import IndyError
from von_anchor import NominalAnchor
from von_anchor.error import ExtantWallet
from von_anchor.frill import do_wait, inis2dict, ppjson
from von_anchor.indytween import Role
from von_anchor.nodepool import NodePool, NodePoolManager
from von_anchor.tails import Tails
from von_anchor.util import AnchorData, NodePoolData, ok_rev_reg_id
from von_anchor.wallet import Wallet


config = {}


class Profile(Enum):
    """
    Enum for tails client profiles.
    """

    ISSUER = 1
    PROVER = 2

    @staticmethod
    def get(token: str) -> 'Profile':
        """
        Return enum instance corresponding to input token.

        :param token: token identifying profile
        :return: enum instance corresponding to input token
        """

        for profile in Profile:
            if token.upper() == profile.name:
                return profile

        return None


def usage() -> None:
    """
    Print usage message.
    """

    print()
    print('Usage: sync.py <config-ini>')
    print()
    print('where <config-ini> represents the path to the configuration file.')
    print()
    print('The operation synchronizes tails files once against the tails file server,')
    print('as per the configured tails client profile.')
    print()
    print('The configuration file has sections and entries as follows:')
    print('  * section [Tails Server]:')
    print('    - host: the hostname or address of the tails server')
    print('    - port: the port on which the tails server listens')
    print('  * section [Tails Client]:')
    print('    - profile: the client profile to adopt; specify')
    print('      - issuer: to upload to the tails file server')
    print('      - prover: to download from the tails file server')
    print('    - tails.dir: the local directory serving as the tails tree')
    print('  * (issuer only) section [Node Pool]:')
    print('    - name: the name of the node pool to which the operation applies')
    print('    - genesis.txn.path: the path to the genesis transaction file')
    print('        for the node pool (may omit if pool already exists)')
    print('  * (issuer only) section [VON Anchor], pertaining to the issuer VON anchor:')
    print("    - seed: the VON anchor's seed (omit if wallet exists)")
    print("    - wallet.name: the VON anchor's wallet name")
    print("    - wallet.type: (default blank) the VON anchor's wallet type")
    print("    - wallet.key: (default blank) the VON anchor's")
    print('        wallet access credential (password) value.')
    print()


def survey(dir_tails: str, host: str, port: int, issuer_did: str = None) -> tuple:
    """
    Return tuple with paths to local tails symbolic links (revocation registry identifiers) and
    revocation registry identifiers of interest on tails server.

    Raise ConnectionError on connection failure.

    :param dir_tails: local tails directory
    :param host: tails server host
    :param port: tails server port
    :param issuer_did: issuer DID of interest for local and remote tails file survey (default all)
    :return: pair (remote paths to tails links, remote rev reg ids)
    """

    loc = Tails.links(dir_tails, issuer_did)
    url = 'http://{}:{}/tails/list/{}'.format(host, port, issuer_did if issuer_did else 'all')
    resp = requests.get(url)
    rem = set(resp.json())

    logging.debug('Survey: local=%s, remote=%s', ppjson(loc), ppjson(rem))
    return (loc, rem)


async def sync_issuer(
        dir_tails: str,
        host: str,
        port: int,
        local_only: set,
        pool: NodePool,
        noman: NominalAnchor) -> None:
    """
    Synchronize for issuer: upload any tails files appearing locally but not remotely.

    :param dir_tails: local tails directory
    :param host: tails server host
    :param port: tails server port
    :param local_only: paths to local tails symbolic links (rev reg ids) without corresponding remote tails files
    :param pool: open node pool
    :param noman: open issuer anchor
    """

    logging.debug('Sync-issuer: local-only=%s', ppjson(local_only))
    if not local_only:
        return

    for rr_id in local_only:
        if not ok_rev_reg_id(rr_id, noman.did):  # restrict POSTs to issuer's own tails files
            logging.debug(
                'Sync-issuer: local-only %s is not a rev reg id for issuer %s (%s)',
                rr_id,
                noman.did,
                noman.wallet.name)
            continue

        epoch = int(time())
        url = 'http://{}:{}/tails/{}/{}'.format(host, port, quote(rr_id), epoch)
        path_tails = Tails.linked(dir_tails, rr_id)
        with open(path_tails, 'rb') as tails_fh:
            tails = tails_fh.read()
            sig = await noman.sign('{}||{}'.format(epoch, tails))
        try:
            resp = requests.post(
                url,
                files={
                    'tails-file': (basename(path_tails), tails),
                    'signature': ('signature', sig)
                })
            logging.info('Upload: url %s status %s', url, resp.status_code)
        except ConnectionError:
            logging.error('POST connection refused: %s', url)


async def sync_prover(dir_tails: str, host: str, port: int, remote_only: set) -> None:
    """
    Synchronize for prover: download any tails files appearing remotely but not locally.

    :param dir_tails: local tails directory
    :param host: tails server host
    :param port: tails server port
    :param remote_only: paths to remote rev reg ids without corresponding local tails files
    """

    if not remote_only:
        return

    for rr_id in remote_only:
        dir_cd_id = Tails.dir(dir_tails, rr_id)
        makedirs(dir_cd_id, exist_ok=True)
        url = 'http://{}:{}/tails/{}'.format(host, port, rr_id)
        try:
            resp = requests.get(url, stream=True)
            if resp.status_code == requests.codes.ok:
                re_tails_hash = re.search('filename="(.+)"', resp.headers['content-disposition'])
                tails_hash = re_tails_hash.group(1) if re_tails_hash.lastindex > 0 else None

                if tails_hash:
                    logging.info('Downloaded: url %s tails-hash %s', url, tails_hash)
                    with open(join(dir_cd_id, tails_hash), 'wb') as fh_tails:
                        for chunk in resp.iter_content(chunk_size=1024):
                            if chunk:
                                fh_tails.write(chunk)
                    Tails.associate(dir_tails, rr_id, tails_hash)
                else:
                    logging.error('Download: url %s, responded with no tails-hash', url)

            else:
                logging.error('Download: url %s, responded with status %s', url, resp.status_code)
        except ConnectionError:
            logging.error('GET connection refused: %s', url)


async def setup(ini_path: str) -> tuple:
    """
    Set configuration from file. If configured profile is issuer, open and return node pool and anchor,
    then register both for shutdown at program exit.

    :param ini_path: path to configuration file
    :return: tuple with profile, open node pool and issuer anchor; (profile, None, None) for prover.
    """

    global config
    config = inis2dict(ini_path)

    profile = Profile.get(config['Tails Client']['profile'])
    if profile != Profile.ISSUER:
        return (profile, None, None)

    pool_data = NodePoolData(
        config['Node Pool']['name'],
        config['Node Pool'].get('genesis.txn.path', None) or None)  # nudge empty value from '' to None

    # Set up node pool ledger config and wallet
    manager = NodePoolManager()
    if pool_data.name not in await manager.list():
        if pool_data.genesis_txn_path:
            await manager.add_config(pool_data.name, pool_data.genesis_txn_path)
        else:
            logging.error(
                'Node pool %s has no ledger configuration but %s specifies no genesis txn path',
                pool_data.name,
                ini_path)
            return 1
    
    pool = manager.get(pool_data.name)
    await pool.open()
    atexit.register(close_pool, pool)

    noman_data = AnchorData(
        Role.USER,
        config['VON Anchor'].get('seed', None) or None,
        config['VON Anchor']['wallet.name'],
        config['VON Anchor'].get('wallet.type', None) or None,
        config['VON Anchor'].get('wallet.key', None) or None)

    wallet = Wallet(
        noman_data.wallet_name,
        noman_data.wallet_type,
        None,
        {'key': noman_data.wallet_key} if noman_data.wallet_key else None)

    if noman_data.seed:
        try:
            await wallet.create(noman_data.seed)
            logging.info('Created wallet {}'.format(noman_data.wallet_name))
        except ExtantWallet:
            logging.warning('Wallet {} already exists: remove seed from configuration file {}'.format(
                noman_data.wallet_name,
                ini_path))

    await wallet.open()
    noman = NominalAnchor(wallet, pool)
    await noman.open()
    atexit.register(close_anchor, noman)

    return (profile, pool, noman)


def close_pool(pool: NodePool) -> None:
    """
    Close node pool.

    :param pool: node pool to close
    """

    do_wait(pool.close())


def close_anchor(anchor: NominalAnchor) -> None:
    """
    Close anchor.

    :param anchor: anchor to close
    """

    do_wait(anchor.wallet.close())
    do_wait(anchor.close())


async def main(profile: Profile, pool: NodePool, noman: NominalAnchor) -> None:
    """
    Survey local and remote content, dispatch to synchronize issuer or prover.

    :param profile: tails client profile
    :param pool: node pool (None for non-issuer)
    :param noman: nominal anchor (None for non-issuer)
    """

    assert profile

    host = config['Tails Server']['host']
    port = config['Tails Server']['port']

    dir_tails = config['Tails Client']['tails.dir']
    if isdir(dir_tails) and port.isdigit():
        port = int(port)
        try:
            if profile == Profile.ISSUER:
                (paths_local, tails_remote) = survey(dir_tails, host, port, noman.did)
                await sync_issuer(
                    dir_tails,
                    host,
                    port,
                    set(basename(p) for p in paths_local) - tails_remote,
                    pool,
                    noman)
            else:
                (paths_local, tails_remote) = survey(dir_tails, host, port)
                await sync_prover(dir_tails, host, port, tails_remote - set(basename(p) for p in paths_local))
        except ConnectionError:
            logging.error('Could not connect to tails server at %s:%s - connection refused', host, port)
    else:
        usage()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)-15s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('urllib').setLevel(logging.ERROR)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('von_anchor').setLevel(logging.WARNING)
    logging.getLogger('indy').setLevel(logging.CRITICAL)

    if len(sys.argv) != 2:
        usage()
    else:
        (profile, pool, noman) = do_wait(setup(sys.argv[1]))
        if profile:
            do_wait(main(profile, pool, noman))
        elif pool:
            logging.error('Configured tails client profile must be issuer or prover.')
