import re
import requests
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, Response, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy import and_, or_, not_, asc, desc, text

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config.from_object('config.ProductionConfig')
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

from models import *


def authorize(f):
    @wraps(f)
    def decorated_function(*args, **kws):
        try:
            if 'user_id' not in session:
                return redirect(url_for('auth'))
        except Exception as e:
            return redirect(url_for('auth'))
        return f(*args, **kws)
    return decorated_function


@app.route('/')
@authorize
def index():
    all_units = db.session.query(Word).with_entities(Word.book_id, Word.unit_id).group_by(
        Word.book_id, Word.unit_id).order_by(asc(Word.book_id), asc(Word.unit_id)).all()

    selected_units = db.session.execute(text(
        f'SELECT "book_id", "unit_id" FROM "words" WHERE "id" IN (SELECT "word_id" FROM "magnets" WHERE "selected" = 1 AND "user_id" = \'{session["user_id"]}\') GROUP BY "book_id", "unit_id"'))
    selected_units = [f'{su[0]}-{su[1]}' for su in selected_units]

    all_units_res = dict()
    for bu in all_units:
        if bu[0] not in all_units_res:
            all_units_res[bu[0]] = list()
        all_units_res[bu[0]].append(bu[1])

    words = db.session.execute(text(
        f'SELECT "magnets"."id" AS "magnet_id", "magnets"."fetch", "words".* FROM "magnets" LEFT JOIN( SELECT "magnet_histories".* FROM "magnet_histories" INNER JOIN ( SELECT MAX ("id") AS "id", "magnet_id" FROM "magnet_histories" GROUP BY "magnet_id" ) AS "X" ON "X"."id" = "magnet_histories"."id" ) AS "MagnetHistoriy" ON "magnets"."id" = "MagnetHistoriy"."magnet_id" INNER JOIN "words" ON "words"."id" = "magnets"."word_id" WHERE "magnets"."selected" = 1 AND "magnets"."user_id" = \'{session["user_id"]}\' ORDER BY ( random() ^ (1.0 / ("MagnetHistoriy"."status_id" + ("magnets"."fetch" * 0.1)) )) ASC'))

    return render_template('index.html', all_units=all_units_res, selected_units=selected_units, words=words)


@app.route('/call-details-api/<word_id>')
@authorize
def call_details_api(word_id):
    word = db.session.query(Word).filter(Word.id == word_id).first()

    db.session.query(Magnet).filter(and_(Magnet.word_id == word_id, Magnet.user_id == session['user_id'])).update({
        'fetch': Magnet.fetch + 1})
    db.session.commit()

    res = requests.get(f'https://api.dictionaryapi.dev/api/v2/entries/en/{word.word_en}').json()

    synonyms = []
    if type(res) is list and 'meanings' in res[0] and type(res[0]['meanings']) is list:
        for m in res[0]['meanings']:
            for s in m['synonyms']:
                synonyms.append(s)
                if len(synonyms) == 3:
                    break

    return jsonify({'synonyms': synonyms}), 200


@app.route('/tts/<word_id>')
@authorize
def tts(word_id):
    word = db.session.query(Word).filter(Word.id == word_id).first()
    file = requests.get(
        'https://voicerss-text-to-speech.p.rapidapi.com/', params={
            'key': 'f7626704a9354878a7a4e31f4604bd4f', 'src': word.word_en, 'hl': 'en-us', 'r': '0', 'c': 'mp3',
            'f': '8khz_8bit_mono'
        }, headers={
            'x-rapidapi-key': 'RAPIDAPI-KEY',
            'x-rapidapi-host': 'voicerss-text-to-speech.p.rapidapi.com'
        }
    )

    return Response(file.content, mimetype=file.headers.get('content-type'))


@app.route('/change-magnet-status/<magnet_id>/<status_id>')
@authorize
def change_magnet_status(magnet_id, status_id):
    magnet_history = MagnetHistory(magnet_id=magnet_id, status_id=status_id)
    db.session.add(magnet_history)
    db.session.commit()
    return jsonify({'msg': 'Magnet status change successfully'}), 200


@app.route('/change-unit-status/<unit_section>/<status_id>')
@authorize
def change_unit_status(unit_section, status_id):
    book_id, unit_id = unit_section.split(',')
    words = db.session.query(Word).filter(and_(Word.book_id == book_id, Word.unit_id == unit_id)).all()
    words_ids = [w.id for w in words]
    if int(status_id):
        existed_words = db.session.query(Magnet.word_id).filter(and_(
            Magnet.user_id == session['user_id'], Magnet.word_id.in_(words_ids))).all()
        existed_words_ids = [w.word_id for w in existed_words]
        new_words_ids = set(words_ids) - set(existed_words_ids)
        db.session.add_all([Magnet(word_id=w, user_id=session['user_id']) for w in new_words_ids])
        db.session.query(Magnet).filter(and_(
            Magnet.word_id.in_(existed_words_ids), Magnet.user_id == session['user_id'])).update({'selected': 1})
        db.session.commit()
        db.session.execute(text(
            f'INSERT INTO "magnet_histories" ("magnet_id", "status_id") SELECT "id" AS "magnet_id", \'1\' AS "status_id" FROM "magnets" WHERE "magnets"."user_id" = \'{session["user_id"]}\' AND "magnets"."id" NOT IN (SELECT "magnet_id" FROM "magnet_histories")'))
    else:
        db.session.query(Magnet).filter(and_(
            Magnet.word_id.in_(words_ids), Magnet.user_id == session['user_id'])).update({'selected': 0})
    db.session.commit()
    return jsonify({'msg': 'Magnet status change successfully'}), 200


@app.route('/auth')
def auth():
    return render_template('auth.html')


@app.route('/login', methods=['POST'])
def login():
    data = request.form
    user = db.session.query(User).filter(User.email == data['email']).first()
    if user is None or not bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({'msg': 'Invalid username or password'}), 400

    session['user_id'] = user.id

    return jsonify({'msg': 'Login successfully'}), 200


@app.route('/register', methods=['POST'])
def register():
    data = request.form
    if db.session.query(User).filter(User.email == data['email']).first() is not None:
        return jsonify({'msg': 'The email is duplicate'}), 400
    if not re.match(r"\"?([-a-zA-Z0-9.`?{}]+@\w+\.\w+)\"?", data['email']):
        return jsonify({'msg': 'Invalid email'}), 400
    if len(data['password']) < 6:
        return jsonify({'msg': 'The password must be at least 6 characters'}), 400
    if data['password'] != data['re_password']:
        return jsonify({'msg': 'The password and re password is not equal'}), 400
    if len(data['fullname']) < 3:
        return jsonify({'msg': 'The Full name must be at least 3 characters'}), 400

    user = User(email=data['email'], fullname=data['fullname'],
                password=bcrypt.generate_password_hash(data['password']).decode())
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id

    return jsonify({'msg': 'Register successfully'}), 200
