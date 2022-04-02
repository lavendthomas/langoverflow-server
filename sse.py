from __future__ import unicode_literals
from dataclasses import dataclass

import os
import json
from datetime import datetime

from dataclasses import dataclass
from random import random
import uuid

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS, cross_origin

from flask_sse import sse

app = Flask(__name__)
app.config['CORS_HEADERS'] = 'Content-Type'

SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY


app = Flask(__name__)
app.config["REDIS_URL"] = "redis://localhost"
app.register_blueprint(sse, url_prefix='/stream')
cors = CORS(app, resources="/*")


@app.route('/')
@cross_origin()
def index():
    return render_template("index.html")

@app.route('/hello')
@cross_origin()
def publish_hello():
    sse.publish({"message": "Hello!"}, type='greeting')
    return "Message sent!"

@app.route('/like_comment', methods=['POST', 'GET'])
@cross_origin()
def like_comment():
    data = request.get_json()
    print(data)

    if data['type'] == 'like':
        user: str = data['user']
        id: uuid.UUID = uuid.UUID(data['id'])

        for c in posted_comments:
            if c.id == id:
                c.add_like(user)

    sse.publish({}, type='comment_liked')
    return "Message sent!"

@app.route('/add_comment', methods=['POST', 'GET'])
@cross_origin()
def add_comment():
    data = json.loads(request.data)
    print(data, type(data))
    
    # Add the comment to the list of comments
    comment = Comment(
        author=data['author'],
        comment=data['comment'],
    )
    posted_comments.append(comment)

    print(posted_comments)

    sse.publish(comment.to_json(), type='comment_added')
    return "Message sent!"


@app.route('/get_comments', methods=['GET'])
@cross_origin()
def get_comments():
    return jsonify(list(map(lambda c: c.to_json(), posted_comments)))

class Comment:
    id: uuid.UUID
    author: str
    comment: str
    date: datetime
    like_count: int = 0
    like_list: set[str] = [] # list of all authors (users) that have liked the comment.

    def __init__(self, author, comment) -> None:
        self.id = uuid.uuid4()
        self.author = author
        self.comment = comment
        self.date=datetime.now()

    def add_like(self, user: str):
        if user not in self.like_list:
            self.like_list.append(user)
            self.like_count += 1

    
    def to_json(self):
        return {
            'id': str(self.id),
            'author': self.author,
            'comment': self.comment,
            'date': self.date.timestamp()
        }

    def from_json(self, json_str):
        data = json.loads(json_str)
        self.id = uuid.UUID(data['id'])
        self.author = data['author']
        self.comment = data['comment']
        self.date = datetime.fromtimestamp(data['date'])

    def __str__(self) -> str:
        return json.dumps(self.to_json())

    def __repr__(self) -> str:
        return self.__str__()

posted_comments: list[Comment] = []



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ['PORT']))