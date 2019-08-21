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

from os import makedirs, unlink
from os.path import basename, dirname, exists, isdir, isfile, islink, join, realpath
from shutil import rmtree
from time import time

from sanic import response
from sanic.request import Request
from sanic.response import HTTPResponse
from von_anchor.error import AbsentRevReg
from von_anchor.tails import Tails
from von_anchor.util import ok_cred_def_id, ok_did, ok_rev_reg_id, rev_reg_id2cred_def_id

from app import app
from app.cache import MEM_CACHE


LOGGER = logging.getLogger(__name__)


async def is_current(epoch: int) -> bool:
    """
    Return whether specified epoch is close enough to current server time, as per configuration (default 300 sec).

    :param epoch: epoch to test
    :return: true for OK, false otherwise
    """

    cfg = await MEM_CACHE.get('config')
    max_skew = max(0, int(cfg.get('Tails Server', {}).get('max.skew.sec', '300')))
    return abs(epoch - int(time())) <= max_skew


@app.get('/did')
async def get_did(request: Request) -> HTTPResponse:
    """
    Get the DID of Tails Server anchor

    :param request: Sanic request
    :return: response containing tails server nominal anchor DID
    """

    tsan = await MEM_CACHE.get('tsan')
    return response.text(tsan.did)


@app.post('/tails/<rr_id:.+>/<epoch:[0-9]+>')
async def post_tails(request: Request, rr_id: str, epoch: int) -> HTTPResponse:
    """
    Post tails file to server, auth-encrypted from issuer (by DID) to tails server anchor.
    Multipart file name must be tails hash.

    :param request: Sanic request structure
    :param rr_id: revocation registry identifier
    :param epoch: current EPOCH time, must be within configured proximity to current server time
    :return: empty text response
    """

    if not ok_rev_reg_id(rr_id):
        LOGGER.error('POST cited bad rev reg id %s', rr_id)
        return response.text('POST cited bad rev reg id {}'.format(rr_id), status=400)
    did = rr_id.split(':')[0]

    if not await is_current(int(epoch)):
        LOGGER.error('POST epoch %s in too far from current server time', epoch)
        return response.text('POST epoch {} is too far from current server time'.format(epoch), status=400)

    tails_hash = request.files['tails-file'][0].name
    if not Tails.ok_hash(tails_hash):
        LOGGER.error('POST attached file named with bad tails file hash %s', tails_hash)
        return response.text('POST attached file named with bad tails file hash {}'.format(tails_hash), status=400)

    dir_tails = join(dirname(dirname(realpath(__file__))), 'tails')
    dir_cd_id = Tails.dir(dir_tails, rr_id)

    makedirs(dir_cd_id, exist_ok=True)

    if Tails.linked(dir_tails, rr_id):
        LOGGER.error('POST attached tails file %s, already present', rr_id)
        return response.text('POST attached tails file {}, already present'.format(rr_id), status=403)

    path_tails_hash = join(dir_cd_id, tails_hash)
    if exists(path_tails_hash):
        LOGGER.error('POST attached tails file %s, already present at %s', rr_id, path_tails_hash)
        return response.text(
            'POST attached tails file {}, already present at {}'.format(rr_id, path_tails_hash),
            status=403)

    tsan = await MEM_CACHE.get('tsan')
    signature = request.files['signature'][0].body
    epoch_tails = '{}||{}'.format(epoch, request.files['tails-file'][0].body)
    if not tsan.verify(epoch_tails, signature, did):
        LOGGER.error('POST attached file %s failed to verify', tails_hash)
        return response.text('POST attached file {} failed to verify'.format(tails_hash), status=400)

    try:
        rev_reg_def = json.loads(await tsan.get_rev_reg_def(rr_id))
        ledger_hash = rev_reg_def.get('value', {}).get('tailsHash', None)
        if ledger_hash != tails_hash:
            LOGGER.error('POST attached tails file hash %s differs from ledger value %s', tails_hash, ledger_hash)
            return response.text(
                'POST attached tails file hash {} differs from ledger value {}'.format(tails_hash, ledger_hash),
                status=400)
    except AbsentRevReg:
        LOGGER.error('POST revocation registry not present on ledger for %s', rr_id)
        return response.text('POST revocation registry not present on ledger for {}'.format(rr_id), status=400)

    with open(path_tails_hash, 'wb') as fh_tails:
        fh_tails.write(request.files['tails-file'][0].body)

    Tails.associate(dir_tails, rr_id, tails_hash)
    LOGGER.info('Associated link %s to POST tails file attachment saved to %s', rr_id, path_tails_hash)

    return response.text('')


@app.get('/tails/<rr_id:.+>')
async def get_tails(request: Request, rr_id: str) -> HTTPResponse:
    """
    Get tails file pertaining to input revocation registry identifier.

    :param request: Sanic request structure
    :param rr_id: rev reg id for revocation registry to which tails file pertains
    :return: HTTP response with tails file, having tails hash as name
    """

    if not ok_rev_reg_id(rr_id):
        LOGGER.error('GET cited bad rev reg id %s', rr_id)
        return response.text('GET cited bad rev reg id {}'.format(rr_id), status=400)

    dir_tails = join(dirname(dirname(realpath(__file__))), 'tails')
    dir_cd_id = Tails.dir(dir_tails, rr_id)

    if not isdir(dir_cd_id):
        LOGGER.error('GET cited rev reg id %s for which tails file dir %s not present', rr_id, dir_cd_id)
        return response.text(
            'GET cited rev reg id {} for which tails file dir {} not present'.format(rr_id, dir_cd_id),
            status=404)

    path_tails = Tails.linked(dir_tails, rr_id)
    if not path_tails:
        LOGGER.error('GET cited rev reg id %s for which tails file not present', rr_id)
        return response.text('GET cited rev reg id {} for which tails file not present'.format(rr_id), status=404)

    LOGGER.info('Fulfilling download GET request for tails file %s associated with rev reg id %s', path_tails, rr_id)
    return await response.file(path_tails, filename=basename(path_tails))


@app.get('/tails/list/<ident:.+>')
async def list_tails(request: Request, ident: str) -> HTTPResponse:
    """
    List tails files by corresponding rev reg ids: all, by rev reg id, by cred def id, or by issuer DID.

    :param request: Sanic request structure
    :param ident: 'all' for no filter; rev reg id, cred def id, or issuer DID to filter by any such identifier
    :return: HTTP response with JSON array of rev reg ids corresponding to available tails files
    """

    rv = []
    dir_tails = join(dirname(dirname(realpath(__file__))), 'tails')

    if ident == 'all':  # list everything: 'all' is not valid base58 so it can't be any case below
        rv = [basename(link) for link in Tails.links(dir_tails)]
    elif ok_rev_reg_id(ident):  # it's a rev reg id
        if Tails.linked(dir_tails, ident):
            rv = [ident]
    elif ok_cred_def_id(ident):  # it's a cred def id (starts with issuer DID)
        rv = [basename(link) for link in Tails.links(dir_tails, ident.split(':')[0])
            if rev_reg_id2cred_def_id(basename(link)) == ident]
    elif ok_did(ident):  # it's an issuer DID
        rv = [basename(link) for link in Tails.links(dir_tails, ident)]
    else:
        LOGGER.error('Token %s is not a valid specifier for tails files', ident)
        return response.text('Token {} is not a valid specifier for tails files'.format(ident), status=400)

    LOGGER.info('Fulfilling GET request listing tails files on filter %s', ident)
    return response.json(rv)


@app.delete('/tails/<ident:.+>/<epoch:[0-9]+>')
async def delete_tails(request: Request, ident: str, epoch: int) -> HTTPResponse:
    """
    Delete tails files by corresponding rev reg ids: all, by rev reg id, by cred def id, or by issuer DID.

    :param request: Sanic request structure
    :param ident: 'all' for no filter; rev reg id, cred def id, or issuer DID to filter by any such identifier
    :param epoch: current EPOCH time, must be within 5 minutes of current server time
    :return: empty text response
    """

    if not await is_current(int(epoch)):
        LOGGER.error('DELETE epoch %s in too far from current server time', epoch)
        return response.text('DELETE epoch {} is too far from current server time'.format(epoch), status=400)

    signature = request.body
    plain = '{}||{}'.format(epoch, ident)

    tsan = await MEM_CACHE.get('tsan')
    if not tsan.verify(plain, signature, tsan.did):
        LOGGER.error('DELETE signature failed to verify')
        return response.text('DELETE signature failed to verify', status=400)

    dir_tails = join(dirname(dirname(realpath(__file__))), 'tails')

    if ident == 'all':  # delete everything -- note that 'all' is not valid base58 so no case below can apply
        if isdir(dir_tails):
            rmtree(dir_tails)
        makedirs(dir_tails, exist_ok=True)

    elif ok_rev_reg_id(ident):  # it's a rev reg id
        path_tails = Tails.linked(dir_tails, ident)
        if path_tails and isfile(path_tails):
            unlink(path_tails)
            LOGGER.info('Deleted %s', path_tails)
        path_link = join(Tails.dir(dir_tails, ident), ident)
        if path_link and islink(path_link):
            unlink(path_link)
            LOGGER.info('Deleted %s', path_link)

    elif ok_cred_def_id(ident):  # it's a cred def id (starts with issuer DID)
        dir_cd_id = join(dir_tails, ident)
        if isdir(dir_cd_id):
            rmtree(dir_cd_id)
            LOGGER.info('Deleted %s', dir_cd_id)
        elif exists(dir_cd_id):  # non-dir is squatting on name reserved for dir: it's corrupt; remove it
            unlink(dir_cd_id)
            LOGGER.info('Deleted spurious non-directory %s', dir_cd_id)

    elif ok_did(ident):  # it's an issuer DID
        dirs_cd_id = {dirname(link) for link in Tails.links(dir_tails, ident)}
        for dir_cd_id in dirs_cd_id:
            if ok_cred_def_id(basename(dir_cd_id)):
                if isdir(dir_cd_id):
                    rmtree(dir_cd_id)
                    LOGGER.info('Deleted %s', dir_cd_id)
                elif exists(dir_cd_id):  # non-dir is squatting on name reserved for dir: it's corrupt; remove it
                    unlink(dir_cd_id)
                    LOGGER.info('Deleted spurious non-directory %s', dir_cd_id)

    else:
        LOGGER.error('Token %s is not a valid specifier for tails files', ident)
        return response.text('Token {} is not a valid specifier for tails files'.format(ident), status=400)

    LOGGER.info('Fulfilled DELETE request deleting tails files on filter %s', ident)
    return response.text('')
