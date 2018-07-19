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


from os.path import dirname, join as pjoin
from sanic import Sanic

from app.cfg import init_logging


DIR_STATIC = pjoin(dirname(__file__), 'static')


# initialize app
app = Sanic(strict_slashes=True)
app.static('/static', DIR_STATIC)
app.static('/favicon.ico', pjoin(DIR_STATIC, 'favicon.ico'))
init_logging()

# load views
from app import views
