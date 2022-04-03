from __future__ import unicode_literals, annotations
from dataclasses import dataclass

import os
import json
from datetime import datetime

import uuid

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from flask_sse import sse

from werkzeug.utils import secure_filename

app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['CORS_HEADERS'] = 'Content-Type'
app.config["REDIS_URL"] = "redis://localhost"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.register_blueprint(sse, url_prefix='/stream')
cors = CORS(app, resources="/*")
db = SQLAlchemy(app)


UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'mp4'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
@cross_origin()
def index():
    return render_template("index.html")


@app.route('/video', methods=['POST', 'GET'])
@cross_origin()
def video():
    if request.method == 'POST':
        f = request.files['file']
        if f and allowed_file(f.filename):
            f.save(os.path.join(UPLOAD_FOLDER, 'vid.mp4'))
            return jsonify({"status": "uploaded", "filename": 'vid.mp4'})
        f.save(os.path.join(UPLOAD_FOLDER, f.filename))

        return jsonify({"status": "uploaded"})
    else:
        return send_from_directory(UPLOAD_FOLDER, request.args.get('vid.mp4'))


@app.route('/login', methods=['POST'])
@cross_origin()
def login():
    data = json.loads(request.data)
    username = data['username']
    user = User(username=username)
    db.session.add(user)
    db.session.commit()
    return user.to_json()

@app.route('/user', methods=['POST'])
@cross_origin()
def user():
    User.query.filter(User.username == 'test').one()

@app.route('/like_comment', methods=['POST', 'GET'])
@cross_origin()
def like_comment():
    data = json.loads(request.data)

    comment_id = int(data["comment_id"])
    user_id: int = str(data["user"])
    user = User.query.filter(User.id == user_id).one()
    
    comment = Comment.query.filter(Comment.id == comment_id).one()

    if data['action'] == 'like' and user not in comment.like_list:
        comment.like_count += 1
        comment.like_list.append(user)
        db.session.commit()
    elif data['action'] == 'unlike' and user in comment.like_list:
        if comment.like_count > 0:
            comment.like_count -= 1
        db.session.commit()


    sse.publish(comment.to_json(), type='comment_liked')
    return "Message sent!"

@app.route('/add_comment', methods=['POST', 'GET'])
@cross_origin()
def add_comment():
    question_id = int(request.args.get('qid'))

    data = json.loads(request.data)
    
    # Add the comment to the list of comments
    comment = Comment(
        question_id=question_id,
        author_id=int(data['author_id']),
        comment=data['comment'],
        like_count=0,
    )
    db.session.add(comment)
    db.session.commit()
    sse.publish(comment.to_json(), type='comment_added')
    return comment.to_json()

@app.route('/get_comments', methods=['GET'])
@cross_origin()
def get_comments():
    question_id = int(request.args.get('qid'))
    return jsonify([c.to_json() for c in Comment.query.filter(Comment.question_id == question_id).order_by(Comment.like_count.desc()).all()])

@app.route('/add_question', methods=['POST'])
@cross_origin()
def add_question():
    data = json.loads(request.data)
    q = Question(
        question=data['question'],
        start_timestamp=data['start_timestamp'],
        end_timestamp=data['end_timestamp']
    )
    db.session.add(q)
    db.session.commit()
    return jsonify(q.to_json())

@app.route('/questions', methods=['GET'])
@cross_origin()
def get_questions():
    return jsonify([q.to_json() for q in Question.query.all()])


@app.route('/change_question', methods=['POST'])
@cross_origin()
def change_question():
    question_id = int(request.args.get('qid'))
    res = Question.query.filter(Question.id == question_id).one()
    sse.publish(res.to_json(), type='change_question')
    return res.to_json()

@app.route('/get_seafood', methods=['GET'])
@cross_origin()
def get_seafood():
    return "🐟️"



tags = db.Table('tags',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('comment_id', db.Integer, db.ForeignKey('comment.id'), primary_key=True)
)

@dataclass
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=False, nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "username": self.username
        }

    def __repr__(self):
        return '<User %r>' % self.username


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    start_timestamp = db.Column(db.Integer, nullable=False)
    end_timestamp = db.Column(db.Integer, nullable=False)
    # comments = db.relationship('Comment', backref='')

    def add_comment(self, comment: Comment):
        self.comments[comment.id] = comment
    
    def to_json(self):
        return {
            'id': str(self.id),
            'question': self.question,
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            # 'comments': [c.to_json() for c in self.comments.values()]
        }
    
    def __str__(self) -> str:
        return json.dumps(self.to_json())

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self) -> int:
        return self.id.__hash__()


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    like_list = db.relationship('User', secondary=tags, lazy='subquery', backref=db.backref("comments", lazy=True))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    question = db.relationship('Question', backref=db.backref('comments'), lazy=True)

    
    def to_json(self):
        return {
            'id': str(self.id),
            'author_id': self.author_id,
            'comment': self.comment,
            'date': self.date,
            'like_count': self.like_count,
            'like_list': [u.to_json() for u in self.like_list]
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

db.create_all()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ['PORT']))
