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
import re
from os import makedirs, sys
from os.path import basename, isdir, join as pjoin

import requests
from requests.exceptions import ConnectionError
from von_anchor.tails import Tails


def usage():
    """
    Print usage message.
    """

    print('\nUsage: sync.py <local-tails-dir> <tails-server-host> <tails-server-port> issuer|prover\n')
    print()
    print('where:')
    print('    <local-tails-dir>:   tails directory on anchor host')
    print('    <tails-server-host>: hostname or IP address of remote tails server')
    print('    <tails-server-port>: port for remote tails server')
    print('    issuer|prover:       issuer to upload local-only tails files, prover to download remote-only')


def survey(dir_tails, host, port):
    """
    Return tuple with paths to local tails symbolic links (revocation registry identifiers) and
    revocation registry identifiers that remote server holds.

    Raise ConnectionError on connection failure.

    :param dir_tails: local root tails directory
    :param host: tails server host
    :param port: tails server port
    :return: pair (remote paths to tails links, remote rev reg ids)
    """

    loc = Tails.links(dir_tails)
    url = 'http://{}:{}/tails/list/all'.format(host, port)
    resp = requests.get(url)
    rem = set(resp.json())

    logging.debug('Survey: local=%s, remote=%s', loc, rem)
    return (loc, rem)


def sync_issuer(dir_tails, host, port, local_only):
    """
    Synchronize for issuer: upload any tails files appearing locally but not remotely.

    :param dir_tails: local root tails directory
    :param host: tails server host
    :param port: tails server port
    :param local_only: paths to local tails symbolic links (rev reg ids) without corresponding remote tails files
    """

    for rr_id in local_only:
        url = 'http://{}:{}/tails/{}'.format(host, port, rr_id)
        with open(Tails.linked(dir_tails, rr_id), 'rb') as fh_tails:
            try:
                resp = requests.post(url, files={'file': fh_tails})
                logging.info('Uploaded: url %s status %s', url, resp.status_code)
            except ConnectionError:
                logging.error('POST Connection refused: %s', url)


def sync_holder_prover(dir_tails, host, port, remote_only):
    """
    Synchronize for issuer: download any tails files appearing remotely but not locally.

    :param dir_tails: local root tails directory
    :param host: tails server host
    :param port: tails server port
    :param remote_only: paths to remote rev reg ids without corresponding local tails files
    """

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
                    with open(pjoin(dir_cd_id, tails_hash), 'wb') as fh_tails:
                        for chunk in resp.iter_content(chunk_size=1024):
                            if chunk:
                                fh_tails.write(chunk)
                    Tails.associate(dir_tails, rr_id, tails_hash)
                else:
                    logging.error('Downloading url %s, responded with no tails-hash', url)

            else:
                logging.error('Downloading url %s, responded with status %s', url, resp.status_code)
        except ConnectionError:
            logging.error('GET Connection refused: %s', url)


def main(dir_tails, host, port, role):
    """
    Survey local and remote content, dispatch to synchronize issuer or holder-prover.
    """

    if isdir(dir_tails) and port.isdigit() and role in ('issuer', 'prover'):
        try:
            (paths_local, tails_remote) = survey(dir_tails, host, port)

            if role == 'issuer':
                sync_issuer(dir_tails, host, port, set(basename(p) for p in paths_local) - tails_remote)
            else:
                sync_holder_prover(dir_tails, host, port, tails_remote - set(basename(p) for p in paths_local))
        except ConnectionError:
            logging.error('Could not survey tails server at %s:%s - connection refused', host, port)
    else:
        usage()

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)-15s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    if len(sys.argv) != 5:
        usage()
    else:
        ARG_DIR_TAILS = sys.argv[1]
        ARG_HOST = sys.argv[2]
        ARG_PORT = sys.argv[3]
        ARG_ROLE = sys.argv[4].lower()

        main(ARG_DIR_TAILS, ARG_HOST, ARG_PORT, ARG_ROLE)
