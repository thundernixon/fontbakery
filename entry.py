# coding: utf-8
# Copyright 2013 The Font Bakery Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# See AUTHORS.txt for the list of Authors and LICENSE.txt for the License.

import gevent.monkey
gevent.monkey.patch_all()

from bakery import create_app, init_app

app = create_app(app_name='bakery')
app.config['DEBUG'] = True
app.config.from_object('config')
app.config.from_pyfile('local.cfg', silent=True)
init_app(app)

if __name__ == '__main__':
    import os
    from werkzeug.wsgi import SharedDataMiddleware
    app = SharedDataMiddleware(app, {
        '/': os.path.join(os.path.dirname(__file__), 'bakery', 'static')
        })
    from socketio.server import SocketIOServer
    SocketIOServer(('0.0.0.0', 5000), app,
        resource="socket.io", policy_server=False, transports=['websocket', 'xhr-polling']).serve_forever()
