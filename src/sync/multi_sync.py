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


from os import sys
from os.path import isdir
from threading import Lock, Timer

from sync import main


LOCK = Lock()


def usage():
    """
    Print usage message.
    """

    print('\nUsage: multi_sync.py <n> <local-tails-dir> <tails-server-host> <tails-server-port> issuer|prover\n')
    print()
    print('where:')
    print('    <n>:                 number of iterations, evenly spaced over a minute (minimum 1, maximum 60)')
    print('    <local-tails-dir>:   tails directory on anchor host')
    print('    <tails-server-host>: hostname or IP address of remote tails server')
    print('    <tails-server-port>: port for remote tails server')
    print('    issuer|prover:       issuer to upload local-only tails files, prover to download remote-only')


def dispatch(dir_tails, host, port, role):
    """
    Dispatch a sync invocation.
    """

    if LOCK.acquire(False):  # demur if sync in progress
        try:
            main(dir_tails, host, port, role)
        finally:
            LOCK.release()


def sched():
    """
    Schedule sync invocations.
    """

    arg_n = sys.argv[1]
    arg_dir_tails = sys.argv[2]
    arg_host = sys.argv[3]
    arg_port = sys.argv[4]
    arg_role = sys.argv[5].lower()

    if arg_n.isdigit() and isdir(arg_dir_tails) and arg_port.isdigit() and arg_role in ('issuer', 'prover'):
        iterations = min(max(1, int(arg_n)), 60)  # 1 <= n <= 60 iterations per minute
        interval = 60.0 / iterations

        threads = []
        for i in range(iterations):
            threads.append(Timer(i * interval, dispatch, [arg_dir_tails, arg_host, arg_port, arg_role]))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    else:
        usage()

if __name__ == '__main__':
    # uncomment to spam the log with every invocation
    # logging.basicConfig(
        # level=logging.INFO,
        # format='%(asctime)-15s: %(message)s',
        # datefmt='%Y-%m-%d %H:%M:%S')
    # logging.info('Invoked {}'.format(' '.join(sys.argv)))

    if len(sys.argv) != 6:
        usage()
    else:
        sched()
