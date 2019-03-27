"""
Copyright 2017-2018 Government of Canada - Public Services and Procurement Canada - buyandsell.gc.ca

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

from os import environ
from pathlib import Path
from shutil import rmtree
from tempfile import gettempdir

import pytest

from indy import wallet, pool, did, ledger


logging.basicConfig(level=logging.WARN)
logging.getLogger('von_tails').setLevel(logging.WARN)
logging.getLogger('von_anchor').setLevel(logging.WARN)
logging.getLogger('indy').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def path_temp():
    logger = logging.getLogger(__name__)
    logger.debug('path_temp: >>>')

    path = Path(gettempdir()).joinpath('indy_client')

    if path.exists():
        logger.debug('path_temp: Cleanup tmp path: %s', path)
        rmtree(str(path))

    logger.debug('path_temp: yield: %r', path)
    yield path

    if path.exists():
        logger.debug('path_temp: Cleanup tmp path: %s', path)
        rmtree(str(path))

    logger.debug('path_temp: <<<')


@pytest.fixture
def path_home() -> Path:
    logger = logging.getLogger(__name__)
    logger.debug('path_home: >>>')

    path = Path.home().joinpath('.indy_client')

    if path.exists():
        logger.debug('path_home: cleaning up home path: %r', path)
        rmtree(str(path))

    logger.debug('path_home: yield: %r', path)
    yield path

    if path.exists():
        logger.debug('path_home: cleaning up home path: %r', path)
        rmtree(str(path))

    logger.debug('path_home: <<<')


@pytest.fixture
def host_port():
    logger = logging.getLogger(__name__)
    logger.debug('host_port: >>>')

    res = environ.get('HOST_PORT', '8808')

    logger.debug('host_port: <<< res: %r', res)
    return res


@pytest.fixture
def pool_ip():
    logger = logging.getLogger(__name__)
    logger.debug('pool_ip: >>>')

    res = environ.get('TEST_POOL_IP', '127.0.0.1')

    logger.debug('pool_ip: <<< res: %r', res)
    return res


@pytest.fixture
def pool_name():
    logger = logging.getLogger(__name__)
    logger.debug('pool_name: >>>')

    res = 'pool1'

    logger.debug('pool_name: <<< res: %r', res)
    return res


@pytest.fixture
def genesis_txn_path(pool_name, path_temp):
    logger = logging.getLogger(__name__)
    logger.debug('genesis_txn_path: >>> pool_name: %r', pool_name)

    res = path_temp.joinpath('{}.txn'.format(pool_name))

    logger.debug('genesis_txn_path: <<< res: %r', res)
    return res


@pytest.fixture
def genesis_txn_count():
    logger = logging.getLogger(__name__)
    logger.debug('genesis_txn_count: >>>')

    res = 4

    logger.debug('genesis_txn_count: <<< res: %r', res)
    return res


@pytest.fixture
def genesis_txn_data(genesis_txn_count, pool_ip):
    logger = logging.getLogger(__name__)
    logger.debug('genesis_txn_data: >>> genesis_txn_count: %r, pool_ip: %r',
        genesis_txn_count,
        pool_ip)

    assert 0 < genesis_txn_count <= 4

    res = '\n'.join(
        [
            '{{"reqSignature":{{}},"txn":{{"data":{{"data":{{"alias":"Node1","blskey":"4N8aUNHSgjQVgkpm8nhNEfDf6txHznoYREg9kirmJrkivgL4oSEimFF6nsQ6M41QvhM2Z33nves5vfSn9n1UwNFJBYtWVnHYMATn76vLuL3zU88KyeAYcHfsih3He6UHcXDxcaecHVz6jhCYz1P2UZn2bDVruL5wXpehgBfBaLKm3Ba","blskey_pop":"RahHYiCvoNCtPTrVtP7nMC5eTYrsUA8WjXbdhNc8debh1agE9bGiJxWBXYNFbnJXoXhWFMvyqhqhRoq737YQemH5ik9oL7R4NTTCz2LEZhkgLJzB3QRQqJyBNyv7acbdHrAT8nQ9UkLbaVL9NBpnWXBTw4LEMePaSHEw66RzPNdAX1","client_ip":"{}","client_port":9702,"node_ip":"{}","node_port":9701,"services":["VALIDATOR"]}},"dest":"Gw6pDLhcBcoQesN72qfotTgFa7cbuqZpkX3Xo6pLhPhv"}},"metadata":{{"from":"Th7MpTaRZVRYnPiabds81Y"}},"type":"0"}},"txnMetadata":{{"seqNo":1,"txnId":"fea82e10e894419fe2bea7d96296a6d46f50f93f9eeda954ec461b2ed2950b62"}},"ver":"1"}}'.format(pool_ip, pool_ip),
            '{{"reqSignature":{{}},"txn":{{"data":{{"data":{{"alias":"Node2","blskey":"37rAPpXVoxzKhz7d9gkUe52XuXryuLXoM6P6LbWDB7LSbG62Lsb33sfG7zqS8TK1MXwuCHj1FKNzVpsnafmqLG1vXN88rt38mNFs9TENzm4QHdBzsvCuoBnPH7rpYYDo9DZNJePaDvRvqJKByCabubJz3XXKbEeshzpz4Ma5QYpJqjk","blskey_pop":"Qr658mWZ2YC8JXGXwMDQTzuZCWF7NK9EwxphGmcBvCh6ybUuLxbG65nsX4JvD4SPNtkJ2w9ug1yLTj6fgmuDg41TgECXjLCij3RMsV8CwewBVgVN67wsA45DFWvqvLtu4rjNnE9JbdFTc1Z4WCPA3Xan44K1HoHAq9EVeaRYs8zoF5","client_ip":"{}","client_port":9704,"node_ip":"{}","node_port":9703,"services":["VALIDATOR"]}},"dest":"8ECVSk179mjsjKRLWiQtssMLgp6EPhWXtaYyStWPSGAb"}},"metadata":{{"from":"EbP4aYNeTHL6q385GuVpRV"}},"type":"0"}},"txnMetadata":{{"seqNo":2,"txnId":"1ac8aece2a18ced660fef8694b61aac3af08ba875ce3026a160acbc3a3af35fc"}},"ver":"1"}}'.format(pool_ip, pool_ip),
            '{{"reqSignature":{{}},"txn":{{"data":{{"data":{{"alias":"Node3","blskey":"3WFpdbg7C5cnLYZwFZevJqhubkFALBfCBBok15GdrKMUhUjGsk3jV6QKj6MZgEubF7oqCafxNdkm7eswgA4sdKTRc82tLGzZBd6vNqU8dupzup6uYUf32KTHTPQbuUM8Yk4QFXjEf2Usu2TJcNkdgpyeUSX42u5LqdDDpNSWUK5deC5","blskey_pop":"QwDeb2CkNSx6r8QC8vGQK3GRv7Yndn84TGNijX8YXHPiagXajyfTjoR87rXUu4G4QLk2cF8NNyqWiYMus1623dELWwx57rLCFqGh7N4ZRbGDRP4fnVcaKg1BcUxQ866Ven4gw8y4N56S5HzxXNBZtLYmhGHvDtk6PFkFwCvxYrNYjh","client_ip":"{}","client_port":9706,"node_ip":"{}","node_port":9705,"services":["VALIDATOR"]}},"dest":"DKVxG2fXXTU8yT5N7hGEbXB3dfdAnYv1JczDUHpmDxya"}},"metadata":{{"from":"4cU41vWW82ArfxJxHkzXPG"}},"type":"0"}},"txnMetadata":{{"seqNo":3,"txnId":"7e9f355dffa78ed24668f0e0e369fd8c224076571c51e2ea8be5f26479edebe4"}},"ver":"1"}}'.format(pool_ip, pool_ip),
            '{{"reqSignature":{{}},"txn":{{"data":{{"data":{{"alias":"Node4","blskey":"2zN3bHM1m4rLz54MJHYSwvqzPchYp8jkHswveCLAEJVcX6Mm1wHQD1SkPYMzUDTZvWvhuE6VNAkK3KxVeEmsanSmvjVkReDeBEMxeDaayjcZjFGPydyey1qxBHmTvAnBKoPydvuTAqx5f7YNNRAdeLmUi99gERUU7TD8KfAa6MpQ9bw","blskey_pop":"RPLagxaR5xdimFzwmzYnz4ZhWtYQEj8iR5ZU53T2gitPCyCHQneUn2Huc4oeLd2B2HzkGnjAff4hWTJT6C7qHYB1Mv2wU5iHHGFWkhnTX9WsEAbunJCV2qcaXScKj4tTfvdDKfLiVuU2av6hbsMztirRze7LvYBkRHV3tGwyCptsrP","client_ip":"{}","client_port":9708,"node_ip":"{}","node_port":9707,"services":["VALIDATOR"]}},"dest":"4PS3EDQ3dW1tci1Bp6543CfuuebjFrg36kLAUcskGfaA"}},"metadata":{{"from":"TWwCRQRZ2ZHMJFn9TzLp7W"}},"type":"0"}},"txnMetadata":{{"seqNo":4,"txnId":"aa5e817d7cc626170eca175822029339a444eb0ee8f0bd20d3b0b76e566fb008"}},"ver":"1"}}'.format(pool_ip, pool_ip)
        ][0:genesis_txn_count])
    logger.debug('genesis_txn_data: <<< res: %r', res)
    return res


@pytest.fixture
def genesis_txn_file(genesis_txn_path, genesis_txn_data):
    logger = logging.getLogger(__name__)
    logger.debug('genesis_txn_file: >>> genesis_txn_path: %r, genesis_txn_data: %r',
                 genesis_txn_path,
                 genesis_txn_data)

    genesis_txn_path.parent.mkdir(parents=True, exist_ok=True)

    with open(str(genesis_txn_path), 'w+') as f:
        f.writelines(genesis_txn_data)

    logger.debug('genesis_txn_file: <<<')


@pytest.fixture
def seed():
    logger = logging.getLogger(__name__)
    logger.debug('seed: >>>')

    res = {
        'trustee': '000000000000000000000000Trustee1',
        'issuer': 'von-tails-issuer0000000000000000',
        'prover': 'von-tails-prover0000000000000000'
    }

    logger.debug('seed: <<< res: %r', res)
    return res
    

@pytest.fixture
def path_cli_ini(path_temp):
    logger = logging.getLogger(__name__)
    logger.debug('path_cli_ini: >>>')

    res = {
        'issuer': Path(path_temp).joinpath('issuer.ini'),
        'prover': Path(path_temp).joinpath('prover.ini'),
        'admin': Path(path_temp).joinpath('admin.ini')
    }

    logger.debug('path_cli_ini: <<< res: %r', res)
    return res


@pytest.fixture
def cli_ini(path_cli_ini, host_port, path_home, path_temp, pool_name, seed, genesis_txn_path, genesis_txn_file):
    logger = logging.getLogger(__name__)
    logger.debug('cli_ini: >>>')

    path_cli_ini['issuer'].parent.mkdir(parents=True, exist_ok=True)
    Path(path_temp).joinpath('tails-prover').mkdir(parents=True, exist_ok=True)

    data = {
        'issuer': {
            '\n'.join([
                '[Tails Server]',
                'host=localhost',
                'port={}'.format(host_port),
                '',
                '[Tails Client]',
                'profile=issuer',
                'tails.dir={}'.format(Path(path_home).joinpath('tails')),
                '',
                '[Node Pool]',
                'name={}'.format(pool_name),
                'genesis.txn.path={}'.format(genesis_txn_path),
                '',
                '[VON Anchor]',
                'name=issuer',
                'seed={}'.format(seed['issuer']),
                'wallet.create=True',
                'wallet.type=',
                'wallet.access='
            ])
        },
        'prover': {
            '\n'.join([
                '[Tails Server]',
                'host=localhost',
                'port={}'.format(host_port),
                '',
                '[Tails Client]',
                'profile=prover',
                'tails.dir={}'.format(Path(path_temp).joinpath('tails-prover'))
            ])
        },
        'admin': {
            '\n'.join([
                '[Tails Server]',
                'host=localhost',
                'port={}'.format(host_port),
                '',
                '[Node Pool]',
                'name={}'.format(pool_name),
                'genesis.txn.path={}'.format(genesis_txn_path),
                '',
                '[VON Anchor]',
                'name=tails-server',
                'seed=${TAILS_SERVER_SEED:-00000000000000000000TailsServer1}',
                'wallet.create=True',
                'wallet.type=',
                'wallet.access='
            ])
        }
    }

    for profile in data:
        with open(str(path_cli_ini[profile]), 'w+') as f:
            f.writelines(data[profile])

    logger.debug('cli_ini: <<<')


@pytest.fixture
def path_setnym_ini(path_temp):
    logger = logging.getLogger(__name__)
    logger.debug('path_setnym_ini: >>>')

    res = {
        'issuer': Path(path_temp).joinpath('setnym-issuer.ini'),
        'prover': Path(path_temp).joinpath('setnym-prover.ini')
    }

    logger.debug('path_setnym_ini: <<< res: %r', res)
    return res


@pytest.fixture
def setnym_ini(path_setnym_ini, pool_name, seed, genesis_txn_path, genesis_txn_file):
    logger = logging.getLogger(__name__)
    logger.debug('setnym_ini: >>>')

    path_setnym_ini['issuer'].parent.mkdir(parents=True, exist_ok=True)

    data = {
        profile: '\n'.join([
            '[Node Pool]',
            'name={}'.format(pool_name),
            'genesis.txn.path={}'.format(genesis_txn_path),
            '',
            '[Trustee Anchor]',
            'name=trustee-anchor',
            'seed={}'.format(seed['trustee']),
            'wallet.create=True',
            'wallet.type=',
            'wallet.access=',
            '',
            '[VON Anchor]',
            'role={}'.format('TRUST_ANCHOR' if profile == 'issuer' else ''),
            'name={}'.format(profile),
            'seed={}'.format(seed[profile]),
            'wallet.create=True',
            'wallet.type=',
            'wallet.access='
        ]) for profile in path_setnym_ini
    }

    for profile in path_setnym_ini:
        with open(str(path_setnym_ini[profile]), "w+") as f:
            f.writelines(data[profile])

    logger.debug("setnym_ini: <<<")
