from __future__ import unicode_literals, annotations
from dataclasses import dataclass

import os
import json
import pickle
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


@app.route('/like_comment', methods=['POST', 'GET'])
@cross_origin()
def like_comment():
    question_id = uuid.UUID(request.args.get('qid'))
    data = json.loads(request.data)

    comment_id = uuid.UUID(data["comment_id"])
    user: str = data['user']
    question = database['posted_questions'][question_id]
    if data['action'] == 'like':
        question.comments[comment_id].add_like(user)
    elif data['action'] == 'unlike':
        question.comments[comment_id].remove_like(user)

    sse.publish({}, type='comment_liked')
    return "Message sent!"

@app.route('/add_comment', methods=['POST', 'GET'])
@cross_origin()
def add_comment():
    print("add_comment")
    question_id = uuid.UUID(request.args.get('qid'))

    data = json.loads(request.data)
    print(data, type(data))
    
    # Add the comment to the list of comments
    comment = Comment(
        author=data['author'],
        comment=data['comment'],
    )
    database['posted_questions'][question_id].add_comment(comment)
    database['posted_questions'][question_id].author = "AnotherPerson"
    print("add_comment, comments: " + str(database['posted_questions'][question_id]))

    sse.publish(comment.to_json(), type='comment_added')
    return "Message sent!"

@app.route('/get_comments', methods=['GET'])
@cross_origin()
def get_comments():
    print("get_comments")
    question_id = uuid.UUID(request.args.get('qid'))
    print("question id: ", question_id)
    try:
        question = database['posted_questions'][question_id]
        print(database['posted_questions'])
        return jsonify([c.to_json() for c in question.comments.values()])
    except KeyError:
        print("Here")
        return jsonify([])

@app.route('/questions', methods=['GET'])
@cross_origin()
def get_questions():
    print("get_questions")
    return jsonify([q.to_json() for q in database['posted_questions'].values()])

@app.route('/dump', methods=['GET'])
@cross_origin()
def dump():
    print("DUMPING THE DAMN DATABASE")
    save()


class Question:
    id: uuid.UUID
    question: str
    start_timestamp: int
    end_timestamp: int
    comments: dict[uuid.UUID, Comment]

    def __init__(self, question: str, start_timestamp: int, end_timestamp: int) -> None:
        """
        :param question: The question to ask
        :param start_timestamp: The start timestamp of the video in seconds
        :param end_timestamp: The end timestamp of the video in seconds
        """
        self.id = uuid.uuid4()
        self.question = question
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.comments = dict()

    def add_comment(self, comment: Comment):
        print("Question: add_comment")
        self.comments[comment.id] = comment
        print("self.comments: " + str(self.comments))
    
    def to_json(self):
        return {
            'id': str(self.id),
            'question': self.question,
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            'comments': [c.to_json() for c in self.comments.values()]
        }
    
    def __str__(self) -> str:
        return json.dumps(self.to_json())

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self) -> int:
        return self.id.__hash__()


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

    def remove_like(self, user: str):
        pass

    
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
    
    def __hash__(self) -> int:
        return self.id.__hash__()


database = {}

def load():
    try:
        with open("database.db", "r") as f:
            database = pickle.load(f)
    except:
        pass

def save():
    with open("database.db", "w") as f:
        pickle.dump(database, f)

questions = [
    Question("What is the best programming language?", 0, 3),
    Question("What is the best framework?", 3, 100)]
if not 'posted_questions' in database:
    database['posted_questions'] = {q.id: q for q in questions}

if __name__ == '__main__':
    try:
        load()
        app.run(host="0.0.0.0", port=int(os.environ['PORT']))
    except KeyboardInterrupt:
        print("SAVING THE DAMN DATABASE")
        save()