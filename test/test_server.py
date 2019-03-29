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


import atexit
import datetime
import json
import pexpect
import pytest
import requests
import socket
import subprocess

from configparser import ConfigParser
from contextlib import closing
from hashlib import sha256
from io import StringIO
from os.path import abspath, basename, dirname, expandvars, isfile, join as join
from requests.exceptions import ConnectionError
from time import sleep, time

from von_anchor import BCRegistrarAnchor, OrgBookAnchor
from von_anchor.error import AbsentSchema, ExtantWallet
from von_anchor.frill import inis2dict, ppjson, Ink
from von_anchor.indytween import SchemaKey
from von_anchor.nodepool import NodePool
from von_anchor.tails import Tails
from von_anchor.util import cred_def_id, schema_id, schema_key
from von_anchor.wallet import Wallet, WalletManager


MANAGE = join(dirname(dirname(abspath(__file__))), 'docker', 'manage')


def shutdown():
    print('\n\n== X == Stopping tails server and node pool')
    rv = pexpect.run('{} stop'.format(MANAGE))


def is_up(host, port):
    rc = 0
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(5)
        rc = sock.connect_ex((host, port))
    return (rc == 0)


def url_for(port, path=''):
    rv = 'http://localhost:{}/{}'.format(port, path).strip('/')  # docker-compose port-forwards
    return rv


def get_http_response(method, port, msg_type, args, proxy_did=None, rc_http=200):
    assert all(isinstance(x, str) for x in args)
    url = url_for(port, msg_type)
    r = method(url, json=json.loads(form_json(msg_type, args, proxy_did=proxy_did)))
    assert r.status_code == rc_http, 'Expected HTTP status code {} - received {}'.format(rc_http, r.status_code)
    return r.json()


class TailsServer:
    def __init__(self, port):
        self._port = port
        self._proc = None
        self._started = False

    @property
    def port(self):
        return self._port

    def is_up(self):
        url = url_for(self._port, 'did')
        try:
            r = requests.get(url)
            return r.status_code == 200
        except ConnectionError:
            return False

    def start(self):
        if self.is_up():
            return False

        self._proc = pexpect.spawn('{} bg --no-ansi'.format(MANAGE))
        rc = self._proc.expect(
            [
                'Starting von_tails ... done.*\r\n',
                'Error.*\r\n',
                pexpect.EOF,
                pexpect.TIMEOUT
            ],
            timeout=20)
        if rc == 1:
            raise ValueError('Tails server startup error: {}'.format(self._proc.after.decode()))
        elif rc == 2:
            raise ValueError('Tails server stopped: {}'.format(self._proc.before.decode()))
        elif rc == 3:
            raise ValueError('Timed out waiting on tails server')

        # wait for startup sequence to complete
        print('\n\nWaiting on tails server for up to 60 seconds:', flush=True)
        for i in range(1, 60):
            print('.', end='' if i % 10 else '{}\n'.format(i), flush=True)
            if self.is_up():
                self._started = True
                return True
            sleep(1)

        raise ValueError('Tails server did not start')


async def get_wallets(wallet_data, open_all, auto_remove=False):
    rv = {}
    w_mgr = WalletManager()
    for name in wallet_data:
        w = None
        creation_data = {'seed', 'did'} & {n for n in wallet_data[name]}  # create for tests when seed or did specifies
        if creation_data:
            config = {
                'id': name,
                **{k: wallet_data[name][k] for k in creation_data},
                'auto_remove': auto_remove
            }
            w = await w_mgr.create(
                config,
                access=wallet_data[name]['wallet.access'],
                replace=True)
        else:
            w = await w_mgr.get({'id': name, 'auto_remove': auto_remove}, access=wallet_data[name]['wallet.access'])
        if open_all:
            await w.open()
        assert w.did
        assert w.verkey
        rv[name] = w
    return rv


def get_post_response(port, msg_type, args, rc_http=200):
    assert all(isinstance(x, str) for x in args)
    url = url_for(port, msg_type)
    r = requests.post(url, json=json.loads(form_json(msg_type, args)))
    assert r.status_code == rc_http, 'Expected HTTP status code {} - received {}'.format(rc_http, r.status_code)
    return r.json()


@pytest.mark.skipif(False, reason='short-circuiting')
@pytest.mark.asyncio
async def test_von_tails(pool_ip, genesis_txn_file, path_cli_ini, cli_ini, path_setnym_ini, setnym_ini):

    print(Ink.YELLOW('\n\n== Testing tails server vs. IP {} =='.format(pool_ip)))

    # Set config for tails clients
    config = {}
    i = 0
    for profile in path_cli_ini:
        cli_config = inis2dict(str(path_cli_ini[profile]))
        config[profile] = cli_config
        with open(path_cli_ini[profile], 'r') as fh_cfg:
            print('\n\n== 0.{} == {} tails sync configuration:\n{}'.format(i, profile, fh_cfg.read()))
        i += 1

    # Start tails server
    print('\n\n== 1 == Starting tails server on port {}'.format(config['issuer']['Tails Server']['port']))
    tsrv = TailsServer(config['issuer']['Tails Server']['port'])
    started = tsrv.start()
    if not started:
        print('\n\n== X == Server already running - stop it to run test from scratch')
        assert False

    assert tsrv.is_up()
    print('\n\n== 2 == Started tails server, docker-compose port-forwarded via localhost:{}'.format(tsrv.port))
    atexit.register(shutdown)

    # Set nyms (operation creates pool if need be)
    i = 0
    setnym_config = {}
    for profile in path_setnym_ini:
        cli_config = inis2dict(str(path_setnym_ini[profile]))
        if profile == 'admin':  # tails server anchor on ledger a priori
            continue
        setnym_config[profile] = cli_config
        with open(path_setnym_ini[profile], 'r') as fh_cfg:
            print('\n\n== 3.{} == {} setnym configuration:\n{}'.format(i, profile, fh_cfg.read()))
        sub_proc = subprocess.run(
            [
                'von_anchor_setnym',
                str(path_setnym_ini[profile])
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL)
        assert not sub_proc.returncode
        i += 1
    print('\n\n== 4 == Setnym ops completed OK')

    # wallets = {profile: Wallet(setnym_config[profile]['VON Anchor']['name']) for profile in setnym_config}
    # wallets['admin'] = Wallet(config['admin']['VON Anchor']['name'])
    wallets = await get_wallets(
        {
            **{profile: setnym_config[profile]['VON Anchor'] for profile in setnym_config},
            'admin': config['admin']['VON Anchor']
        },
        open_all=False)

    # Open pool and anchors, issue creds to create tails files
    async with wallets['issuer'] as w_issuer, (
            wallets['prover']) as w_prover, (
            NodePool(config['issuer']['Node Pool']['name'])) as pool, (
            BCRegistrarAnchor(w_issuer, pool)) as ian, (
            OrgBookAnchor(w_prover, pool)) as pan:

        # Get nyms from ledger for display
        i = 0
        for an in (ian, pan):
            print('\n\n== 5.{} == {} nym on ledger: {}'.format(i, an.wallet.name, ppjson(await an.get_nym())))
            i += 1

        # Publish schema to ledger
        S_ID = schema_id(ian.did, 'rainbow', '{}.0'.format(int(time())))
        schema_data = {
            'name': schema_key(S_ID).name,
            'version': schema_key(S_ID).version,
            'attr_names': [
                'numeric',
                'sha256'
            ]
        }

        S_KEY = schema_key(S_ID)
        try:
            await ian.get_schema(S_KEY)  # may exist (almost certainly not)
        except AbsentSchema:
            await ian.send_schema(json.dumps(schema_data))
        schema_json = await ian.get_schema(S_KEY)
        schema = json.loads(schema_json)
        print('\n\n== 6 == SCHEMA [{} v{}]: {}'.format(S_KEY.name, S_KEY.version, ppjson(schema)))
        assert schema  # should exist now

        # Setup link secret for creation of cred req or proof
        await pan.create_link_secret('LinkSecret')

        # Issuer anchor create, store, publish cred definitions to ledger; create cred offers
        await ian.send_cred_def(S_ID, revocation=True)

        cd_id = cred_def_id(S_KEY.origin_did, schema['seqNo'], pool.protocol)

        assert ((not Tails.unlinked(ian.dir_tails)) and
            [f for f in Tails.links(ian.dir_tails, ian.did) if cd_id in f])

        cred_def_json = await ian.get_cred_def(cd_id)  # ought to exist now
        cred_def = json.loads(cred_def_json)
        print('\n\n== 7.0 == Cred def [{} v{}]: {}'.format(
            S_KEY.name,
            S_KEY.version,
            ppjson(json.loads(cred_def_json))))
        assert cred_def.get('schemaId', None) == str(schema['seqNo'])

        cred_offer_json = await ian.create_cred_offer(schema['seqNo'])
        cred_offer = json.loads(cred_offer_json)
        print('\n\n== 7.1 == Credential offer [{} v{}]: {}'.format(
            S_KEY.name,
            S_KEY.version,
            ppjson(cred_offer_json)))

        (cred_req_json, cred_req_metadata_json) = await pan.create_cred_req(cred_offer_json, cd_id)
        cred_req = json.loads(cred_req_json)
        print('\n\n== 8 == Credential request [{} v{}]: metadata {}, cred {}'.format(
            S_KEY.name,
            S_KEY.version,
            ppjson(cred_req_metadata_json),
            ppjson(cred_req_json)))
        assert json.loads(cred_req_json)

        # Issuer anchor issues creds and stores at HolderProver: get cred req, create cred, store cred
        cred_data = []

        CREDS = 450  # enough to build 4 rev regs
        print('\n\n== 9 == creating and storing {} credentials:'.format(CREDS))
        for number in range(CREDS):
            (cred_json, _) = await ian.create_cred(
                cred_offer_json,
                cred_req_json,
                {
                    'numeric': str(number),
                    'sha256': sha256(str(number).encode()).hexdigest(),
                }
            )

            cred_id = await pan.store_cred(cred_json, cred_req_metadata_json)
            print('.', end='' if (number + 1) % 100 else '{}\n'.format(number + 1), flush=True)

        # Exercise list view, least to most specific
        for tails_list_path in ('all', ian.did, cd_id):
            url = url_for(tsrv.port, 'tails/list/{}'.format(tails_list_path))
            r = requests.get(url)
            assert r.status_code == 200
            assert not r.json()
        rr_ids_up = {basename(link) for link in Tails.links(ian.dir_tails, ian.did)}
        for rr_id in rr_ids_up:
            url = url_for(tsrv.port, 'tails/list/{}'.format(rr_id))
            r = requests.get(url)
            assert r.status_code == 200
            assert not r.json()
        print('\n\n== 10 == All listing views at server come back OK and empty as expected')

        rv = pexpect.run('python ../src/sync/sync.py {}'.format(path_cli_ini['issuer']))
        print('\n\n== 11 == Issuer sync uploaded local tails files')

        for tails_list_path in ('all', ian.did, cd_id):
            url = url_for(tsrv.port, 'tails/list/{}'.format(tails_list_path))
            r = requests.get(url)
            assert r.status_code == 200
            assert {rr for rr in r.json()} == rr_ids_up
        for rr_id in rr_ids_up:
            url = url_for(tsrv.port, 'tails/list/{}'.format(rr_id))
            r = requests.get(url)
            assert r.status_code == 200
            assert r.json() == [rr_id]  # list with one rr_id should come back

        rv = pexpect.run('python ../src/sync/sync.py {}'.format(path_cli_ini['prover']))
        print('\n\n== 12 == Prover sync downloaded remote tails files')

        rr_ids_down = {basename(link) for link in Tails.links(config['prover']['Tails Client']['tails.dir'], ian.did)}
        assert rr_ids_down == rr_ids_up

        # Exercise admin-delete
        rv = pexpect.run('python ../src/admin/delete.py {} all'.format(path_cli_ini['admin']))
        print('\n\n== 13 == Admin called for deletion at tails server')

        # Check tails server deletion
        url = url_for(tsrv.port, 'tails/list/all')
        r = requests.get(url)
        assert r.status_code == 200
        assert not r.json()
        print('\n\n== 14 == All listing views at server come back OK and empty as expected')

        # Remove tails server anchor wallet
        await wallets['admin'].remove()
        print('\n\n== 15 == Removed admin (tails server anchor {}) wallet'.format(wallets['admin'].name))
