#!/bin/bash

#
# Copyright 2017-2020 Government of Canada - Public Services and Procurement Canada - buyandsell.gc.ca
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

export HOST_IP=${HOST_IP:-0.0.0.0}
export HOST_PORT=${HOST_PORT}
export RUST_LOG=${RUST_LOG:-error}
export TEST_POOL_IP=${TEST_POOL_IP:-10.0.0.2}

cd "${HOME}"/src
von_anchor_setnym app/config/config.ini
RV=$?
if [ "${RV}" -eq "0" ]
then
    python -m sanic app.app --host=${HOST_IP} --port=${HOST_PORT}
else
    echo "FATAL: Could not set VON Tails anchor cryptonym on ledger"
fi
exit ${RV}
