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
import logging.config

from configparser import ConfigParser
from os import makedirs
from os.path import dirname, expandvars, isfile, join, realpath

from von_anchor.frill import do_wait, inis2dict

from app.cache import MEM_CACHE


def init_logging() -> None:
    """
    Initialize logging configuration.
    """

    dir_log = join(dirname(realpath(__file__)), 'log')
    makedirs(dir_log, exist_ok=True)
    path_log = join(dir_log, 'von_tails.log')

    logging.basicConfig(
        filename=path_log,
        level=logging.INFO,
        format='%(asctime)-15s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('asyncio').setLevel(logging.ERROR)
    logging.getLogger('aiocache').setLevel(logging.ERROR)
    logging.getLogger('indy').setLevel(logging.CRITICAL)
    logging.getLogger('von_anchor').setLevel(logging.INFO)
    logging.getLogger('von_tails').setLevel(logging.INFO)


def set_config() -> dict:
    """
    Read configuration file content into memory cache.

    :return: configuration dict
    """

    ini_path = join(dirname(realpath(__file__)), 'config', 'config.ini')

    do_wait(MEM_CACHE.delete('config'))
    do_wait(MEM_CACHE.set('config', inis2dict(ini_path)))

    return do_wait(MEM_CACHE.get('config'))
