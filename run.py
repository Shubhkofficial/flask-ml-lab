# Issues which needs to be fixed
# 1) Password needs to be sent in an encrypted manner, we can use JWT/OAuth
# 2) Code can be modularised and made more structured
# 3) Instead of storing the files on the server, we can use Cloud storage such as S3
# 4) We can create generic and reusable functions
# 5) Exceptions handling and many checking needs to be addressed such as while storing
# a file checking if teh directory is created or not?

from flask import Flask, send_file, request, abort, jsonify
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import datetime
from sqlalchemy import insert, update
from flask_cors import CORS, cross_origin
import json
import os
import uuid
import numpy as np
import random
import cv2

app = Flask(__name__)
api = Api(app)
CORS(app, support_credentials=True)

# Connection string stored in app config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET'] = 'SECRET123'
# Creating a DB instance
db = SQLAlchemy(app)
FILE_PATH = '/Users/shubhk/Downloads/ImageFiles'

ALLOWED_FILES_EXTENSIONS = {'pdf', 'png', 'jpeg', 'svg', 'jpg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FILES_EXTENSIONS


# Table Creation
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(30), nullable=False, unique=True)
    created_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class ImgFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(20), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    created_by = db.Column(db.String(20), nullable=False)
    file_class = db.Column(db.String(100), nullable=False)
    x1 = db.Column(db.Integer)
    x2 = db.Column(db.Integer)
    y1 = db.Column(db.Integer)
    y2 = db.Column(db.Integer)


with app.app_context():
    print('sup')
    db.create_all()
    # users = User.query.all()


@app.route('/', methods=['GET', 'POST'])
def home():
    return 'Welcome to ML Lab'


@app.route('/register', methods=['POST'])
@cross_origin(supports_credentials=True)
def create_account():
    req = json.loads(request.data)
    username, email, password = req['username'], req['email'], req['password']
    res1 = User.query.filter_by(username=username).first()
    res2 = User.query.filter_by(email=email).first()
    if not res1 and not res2:
        # Can create User
        users = User.query.all()
        stmt = insert(User).values(id=len(users) + 1, username=username, email=email, password=password,
                                   created_date=datetime.datetime.now())
        compiled = stmt.compile()
        with db.engine.connect() as conn:
            conn.execute(compiled)
            conn.commit()
            return jsonify(success=True)
    if res1:
        return 'Userame already exists. Choose another', 403
    return 'Email already exists. Choose another', 403


@app.route('/login', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def validate():
    username = request.args['username']
    password = request.args['password']
    res = User.query.filter_by(username=username).first()
    if not res:
        return abort(404)
    if res.password != password:
        return jsonify({'message': 'Incorrect Login Credentials'})
    return jsonify(success=True)


@app.route('/userMatched', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def user_matched():
    username = request.args['username']
    email = request.args['email']
    res = User.query.filter_by(username=username, email=email).first()
    if not res:
        return 'User Does not Exist', 404
    return jsonify(success=True)


@app.route('/getAllImages', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def get_all_files():
    username = request.args['username']
    ret_obj = []
    res = ImgFile.query.filter_by(created_by=username).all()
    if not res:
        return []
    for _ in res:
        ret_obj.append({
            'id': _.id,
            'filename': _.filename,
            'username': _.created_by,
            'date': _.created_date,
            'class': _.file_class
        })
    return jsonify(ret_obj)

    # S3 connection code


@app.route('/upload', methods=['POST'])
@cross_origin(supports_credentials=True)
def upload_to_server():
    username, class_name = request.args['username'], request.args['class_name']
    images = ImgFile.query.all()
    id = len(images) + 1
    uploaded_file = request.files['attach']
    if not allowed_file(uploaded_file.filename):
        return "FILE TYPE NOT ALLOWED", 403

    new_filename = uuid.uuid4().hex + '.' + uploaded_file.filename.rsplit('.', 1)[1].lower()
    uploaded_file.save(os.path.join(FILE_PATH, new_filename))

    stmt = insert(ImgFile).values(id=id, created_by=username, file_class=class_name, filename=new_filename,
                                  created_date=datetime.datetime.now())
    compiled = stmt.compile()
    with db.engine.connect() as conn:
        conn.execute(compiled)
        conn.commit()
        return jsonify(success=True)


@app.route('/getFile', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def get_file():
    filename = request.args['filename']
    return send_file(os.path.join(FILE_PATH, filename), mimetype='image/gif')


@app.route('/getCoordinates', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def get_coordinates():
    filename = request.args['filename']
    res = ImgFile.query.filter_by(filename=filename).first()
    coordinates = {
        'x1': res.x1 if res.x1 else 0,
        'x2': res.x2 if res.x2 else 0,
        'y1': res.y1 if res.y1 else 0,
        'y2': res.y2 if res.y2 else 0
    }
    return jsonify(coordinates)


@app.route('/saveCoordinates', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def save_coordinates():
    req = json.loads(request.data)
    x1, x2, y1, y2 = req['x1'], req['x2'], req['y1'], req['y2']
    stmt = update(ImgFile).where(ImgFile.filename == request.args['filename']
                                 ).values(x1=x1, x2=x2, y1=y1, y2=y2)
    compiled = stmt.compile()
    with db.engine.connect() as conn:
        conn.execute(compiled)
        conn.commit()
        return jsonify(success=True)
    return abort(500)


@app.route('/noise', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def sp_noise(prob=0.1):
    filename = request.args['filename']
    _ = filename.split('.')
    f, e = _[0], _[1]
    image = cv2.imread(os.path.join(FILE_PATH, filename), 0)
    output = np.zeros(image.shape, np.uint8)
    thres = 1 - prob
    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            rdn = random.random()
            if rdn < prob:
                output[i][j] = 0
            elif rdn > thres:
                output[i][j] = 255
            else:
                output[i][j] = image[i][j]

    new_filename = f + '_noise.' + e

    old_img = ImgFile.query.filter_by(filename=filename).first()
    cv2.imwrite(os.path.join(FILE_PATH, new_filename), output)

    stmt = insert(ImgFile).values(id=len(ImgFile.query.all()) + 1, created_by=old_img.created_by,
                                  file_class=old_img.file_class, filename=new_filename,
                                  created_date=datetime.datetime.now())
    compiled = stmt.compile()
    with db.engine.connect() as conn:
        conn.execute(compiled)
        conn.commit()
        return send_file(os.path.join(FILE_PATH, f + '_noise.' + e), mimetype='image/gif')

    return 'Some Issue', 500


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    app.run(port='5001')
