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


from os.path import dirname, join
from sanic import Sanic

from app.cache import MEM_CACHE
from app.cfg import init_logging, set_config
from app.bootseq import boot


DIR_STATIC = join(dirname(__file__), 'static')


# initialize app
app = Sanic(strict_slashes=True)
app.static('/static', DIR_STATIC)
app.static('/favicon.ico', join(DIR_STATIC, 'favicon.ico'))
init_logging()
set_config()

@app.listener('before_server_stop')
async def cleanup(app, loop):
    tsan = await MEM_CACHE.get('tsan')
    if tsan is not None:
        await tsan.wallet.close()
        await tsan.close()

    pool = await MEM_CACHE.get('pool')
    if pool is not None:
        await pool.close()

# start
boot()

# load views
from app import views
