from __future__ import unicode_literals

import os

from flask import Flask, render_template, jsonify
from flask_cors import CORS, cross_origin

from flask_sse import sse

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY


app = Flask(__name__)
app.config["REDIS_URL"] = "redis://localhost"
app.register_blueprint(sse, url_prefix='/stream')


@app.route('/')
@cross_origin()
def index():
    return render_template("index.html")

@app.route('/hello')
@cross_origin()
def publish_hello():
    sse.publish({"message": "Hello!"}, type='greeting')
    return "Message sent!"


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ['PORT']))

# pip install -U flask-cors