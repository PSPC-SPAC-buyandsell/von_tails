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


import logging

from os import makedirs, unlink
from os.path import abspath, basename, dirname, exists, isdir, isfile, islink, join as pjoin
from shutil import rmtree

from sanic import response
from sanic.request import File as SanicReqFile
from sanic.exceptions import Forbidden, InvalidUsage, NotFound
from von_anchor.tails import Tails
from von_anchor.util import ok_cred_def_id, ok_did, ok_rev_reg_id, rev_reg_id2cred_def_id

from app import app

LOGGER = logging.getLogger(__name__)


@app.post('/tails/<rr_id:.+>')
async def post_tails(request, rr_id):
    """
    Post tails file to server. Multipart file name must be tails hash.

    :param request: Sanic request structure
    :param rr_id: rev reg id for revocation registry to which tails file pertains
    :return: empty text string
    """

    if not ok_rev_reg_id(rr_id):
        LOGGER.error('POST cited bad rev reg id %s', rr_id)
        raise InvalidUsage('POST cited bad rev reg id {}'.format(rr_id))

    # curl uses 'data', python requests uses 'file', there may be others
    req_key = set(k for k in request.files
        if request.files[k]
        and isinstance(request.files[k], list)
        and isinstance(request.files[k][0], SanicReqFile)).pop()
    tails_hash = request.files[req_key][0].name
    if not Tails.ok_hash(tails_hash):
        LOGGER.error('POST attached file named with bad tails file hash %s', tails_hash)
        raise InvalidUsage('POST attached file named with bad tails file hash {}'.format(tails_hash))

    dir_tails = pjoin(dirname(dirname(abspath(__file__))), 'tails')
    dir_cd_id = Tails.dir(dir_tails, rr_id)
    makedirs(dir_cd_id, exist_ok=True)

    if Tails.linked(dir_tails, rr_id):
        LOGGER.error('POST attached tails file %s, already present', rr_id)
        raise Forbidden('POST attached tails file {}, already present'.format(rr_id))

    path_tails_hash = pjoin(dir_cd_id, tails_hash)
    if exists(path_tails_hash):
        LOGGER.error('POST attached tails file %s, already present at %s', rr_id, path_tails_hash)
        raise Forbidden('POST attached tails file {}, already present at {}'.format(rr_id, path_tails_hash))

    with open(path_tails_hash, 'wb') as fh_tails:
        fh_tails.write(request.files[req_key][0].body)

    Tails.associate(dir_tails, rr_id, tails_hash)
    LOGGER.info('Associated link %s to POST tails file attachment saved to %s', rr_id, path_tails_hash)

    return response.text('')


@app.get('/tails/<rr_id:.+>')
async def get_tails(request, rr_id):
    """
    Get tails file pertaining to input revocation registry identifier.

    :param request: Sanic request structure
    :param rr_id: rev reg id for revocation registry to which tails file pertains
    :return: tails file, with tails hash as name
    """

    if not ok_rev_reg_id(rr_id):
        LOGGER.error('GET cited bad rev reg id %s', rr_id)
        raise InvalidUsage('GET cited bad rev reg id {}'.format(rr_id))

    dir_tails = pjoin(dirname(dirname(abspath(__file__))), 'tails')
    dir_cd_id = Tails.dir(dir_tails, rr_id)

    if not isdir(dir_cd_id):
        LOGGER.error('GET cited rev reg id %s for which tails file dir %s not present', rr_id, dir_cd_id)
        raise NotFound('GET cited rev reg id {} for which tails file dir {} not present'.format(rr_id, dir_cd_id))

    path_tails = Tails.linked(dir_tails, rr_id)
    if not path_tails:
        LOGGER.error('GET cited rev reg id %s for which tails file not present', rr_id)
        raise NotFound('GET cited rev reg id {} for which tails file not present'.format(rr_id))

    LOGGER.info('Fulfilling download GET request for tails file %s associated with rev reg id %s', path_tails, rr_id)
    return await response.file(path_tails, filename=basename(path_tails))


@app.get('/tails/list/<ident:.+>')
async def list_tails(request, ident):
    """
    List tails files by corresponding rev reg ids: all, by rev reg id, by cred def id, or by issuer DID.

    :param request: Sanic request structure
    :param ident: 'all' for no filter; rev reg id, cred def id, or issuer DID to filter by any such identifier
    :return: JSON array of rev reg ids corresponding to tails files available
    """

    rv = []
    dir_tails = pjoin(dirname(dirname(abspath(__file__))), 'tails')

    if ident == 'all':  # list everything: 'all' is not valid base58 so it can't be any case below
        rv = [basename(link) for link in Tails.links(dir_tails)]
    elif ok_rev_reg_id(ident) and Tails.linked(dir_tails, ident):  # it's a rev reg id
        rv = [ident]
    elif ok_cred_def_id(ident):  # it's a cred def id (starts with issuer DID)
        rv = [basename(link) for link in Tails.links(dir_tails, ident.split(':')[0])
            if rev_reg_id2cred_def_id(basename(link)) == ident]
    elif ok_did(ident):  # it's an issuer DID
        rv = [basename(link) for link in Tails.links(dir_tails, ident)]
    else:
        LOGGER.error("Token %s must be 'all', rev reg id, cred def id, or issuer DID", ident)
        raise InvalidUsage("Token {} must be 'all', rev reg id, cred def id, or issuer DID".format(ident))

    LOGGER.info('Fulfilling GET request listing tails files on filter %s', ident)
    return response.json(rv)


@app.delete('/tails/del/<ident:.+>')
async def delete_tails(request, ident):
    """
    Delete tails files by corresponding rev reg ids: all, by rev reg id, by cred def id, or by issuer DID.

    :param request: Sanic request structure
    :param ident: 'all' for no filter; rev reg id, cred def id, or issuer DID to filter by any such identifier
    :return: empty text string
    """

    dir_tails = pjoin(dirname(dirname(abspath(__file__))), 'tails')

    if ident == 'all':  # delete everything: 'all' is not valid base58 so it can't be any case below
        rmtree(dir_tails)
        makedirs(dir_tails, exist_ok=True)

    elif ok_rev_reg_id(ident):  # it's a rev reg id
        path_tails = Tails.linked(dir_tails, ident)
        if path_tails and isfile(path_tails):
            unlink(path_tails)
            LOGGER.info('Deleted %s', path_tails)
        path_link = pjoin(Tails.dir(dir_tails, ident), ident)
        if path_link and islink(path_link):
            unlink(path_link)
            LOGGER.info('Deleted %s', path_link)

    elif ok_cred_def_id(ident):  # it's a cred def id (starts with issuer DID)
        dir_cd_id = pjoin(dir_tails, ident)
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
        LOGGER.error('Token %s must be rev reg id, cred def id, or issuer DID', ident)
        raise InvalidUsage('Token {} must be rev reg id, cred def id, or issuer DID'.format(ident))

    LOGGER.info('Fulfilled DELETE request deleting tails files on filter %s', ident)
    return response.text('')
