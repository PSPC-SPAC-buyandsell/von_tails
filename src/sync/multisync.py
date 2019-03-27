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
from threading import Lock, Timer

from von_anchor import NominalAnchor
from von_anchor.frill import do_wait

from .sync import Profile, main, setup


LOCK = Lock()


def usage() -> None:
    """
    Print usage message.
    """

    print()
    print('Usage: multisync.py <n> <config-ini>')
    print()
    print('where:')
    print('    * <n> represents the number (1-30) of iterations, spaced over a minute')
    print('    * <config-ini> represents the path to the configuration file.')
    print()
    print('Each iteration synchronizes tails files against the server as per configuration.')
    print()
    print('See sync.py for configuration file details.')
    print()


def dispatch(profile: Profile, noman: NominalAnchor) -> None:
    """
    Dispatch a sync invocation.

    :param profile: tails client profile
    :param noman: open nominal anchor or None
    """

    if LOCK.acquire(False):  # demur if sync in progress
        try:
            do_wait(main(profile, noman))
        finally:
            LOCK.release()


def sched() -> None:
    """
    Schedule sync invocations for dispatch evenly over a minute as per script arguments.
    """

    arg_n = sys.argv[1]

    if arg_n.isdigit():
        arg_config_ini = sys.argv[2]
        (profile, noman) = do_wait(setup(arg_config_ini))

        iterations = min(max(1, int(arg_n)), 30)  # 1 <= n <= 60 iterations per minute
        interval = 60.0 / iterations

        threads = []
        for i in range(iterations):
            threads.append(Timer(i * interval, dispatch, [profile, noman]))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    else:
        usage()

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)-15s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    # uncomment to spam the log with every invocation
    # logging.info('Invoked {}'.format(' '.join(sys.argv)))

    logging.getLogger('urllib').setLevel(logging.ERROR)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('von_anchor').setLevel(logging.WARNING)
    logging.getLogger('indy').setLevel(logging.CRITICAL)

    if len(sys.argv) != 3:
        usage()
    else:
        sched()
