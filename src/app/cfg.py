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
import logging.config

from os import makedirs
from os.path import abspath, dirname, join as pjoin


def init_logging():
    """
    Initialize logging configuration.
    """

    dir_log = pjoin(dirname(abspath(__file__)), 'log')
    makedirs(dir_log, exist_ok=True)
    path_log = pjoin(dir_log, 'von_tails.log')

    logging.basicConfig(
        filename=path_log,
        level=logging.INFO,
        format='%(asctime)-15s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger('asyncio').setLevel(logging.ERROR)
    logging.getLogger('von_tails').setLevel(logging.INFO)
    logging.getLogger('requests').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
