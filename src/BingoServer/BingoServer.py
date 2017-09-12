import json
import random

from flask import Flask, request, jsonify, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy

from BingoServer.bingo import BingoController, DrawListener, GameSpeed

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:hayesj3@localhost:5432/Bingo'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Gives a warning if not set
app.secret_key = '\x91\x15\xa8\xdd\xcf\xdd\xd8d\xcfs\x99\xe5\x03L\xf7\x81d\x04\x19~\x96\xe8\xec\xda'
db = SQLAlchemy(app)


# class Bingo(db.Model):
#    id = db.Column(db.Integer, primary_key=True)
#    game_session = db.relationship('Session', backref=db.backref('Bingo', lazy='joined'), lazy='select')
#
#    def __init__(self, game_session):
#        self.game_session = game_session
#
#    def __repr__(self):
#        return 'Bingo %r, Session %r' % (self.id, self.game_session.id)


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140))
    desc = db.Column(db.String(140))
    private = db.Column(db.Boolean)
    max_players = db.Column(db.Integer)
    cur_players = db.Column(db.Integer)
    boards = db.relationship('Board', backref=db.backref('Session', lazy='joined'), lazy='select')

    def __init__(self, name='Bingo', desc='A Bingo Session', private=False, max_players=16):
        self.name = name
        self.desc = desc
        self.private = private
        self.max_players = max_players
        self.cur_players = 0

    def __repr__(self):
        return 'Session %r(%r), %r' % (self.name, self.id, self.description)


class Board(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	session_id = db.Column(db.Integer, db.ForeignKey('session.id'), primary_key=True)
	b_col = db.Column(db.PickleType)
	i_col = db.Column(db.PickleType)
	n_col = db.Column(db.PickleType)
	g_col = db.Column(db.PickleType)
	o_col = db.Column(db.PickleType)

    def __init__(self, player_num, session_id):
	    self.id = player_num
        self.session_id = session_id
        self.b_col = make_rand_list(1, 20, 5)
        self.i_col = make_rand_list(21, 40, 5)
        self.n_col = make_rand_list(41, 60, 5)
        self.g_col = make_rand_list(61, 80, 5)
        self.o_col = make_rand_list(81, 100, 5)

    def __repr__(self):
        return 'Session %r(%r), %r' % (self.name, self.id, self.description)


def make_rand_list(lbound, ubound, cnt):
    rand_list = []
    i = 0
    while i < cnt:
        n = random.randrange(lbound, ubound, 1)
        if n in rand_list:
            continue
        else:
	        rand_list.append(n)
            i += 1
    return rand_list


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Session):
            boards = list(iter(obj.boards))
            return {
                "uri": '/bingo/sessions/%d' % obj.id,
                "name": obj.name,
                "desc": obj.desc,
                "private": obj.private,
                "max_players": obj.max_players,
                "cur_players": obj.cur_players,
                "boards": boards
            }
        elif isinstance(obj, Board):
            return {
	            "uri": '/bingo/sessions/%d/boards/%d' % (obj.session_id, obj.id),
                "b":  obj.b_col,
                "i":  obj.i_col,
                "n":  obj.n_col,
                "g":  obj.g_col,
                "o":  obj.o_col
            }
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


@app.route('/')
def index():
    return redirect(url_for('static', filename='index.html'))


@app.route('/bingo', methods=['GET'])
def get_bingo():
    return redirect(url_for('retrieve_sessions'))


@app.route('/bingo/sessions', methods=['GET'])
def retrieve_sessions():
    sessions = Session.query.filter_by(private=False).all()
    return make_response(json.dumps(sessions, cls=CustomEncoder), 200)


@app.route('/bingo/sessions/<int:session_id>', methods=['GET'])
def join_session(session_id):
    session = Session.query.filter_by(id=session_id).first()
    if session is None:
        return make_response(jsonify({'error': 'Session not found!'}), 404)
    return make_response(json.dumps(session, cls=CustomEncoder), 200)


@app.route('/bingo/sessions/<int:session_id>/boards/<int:board_id>', methods=['GET'])
def retrieve_board(session_id, board_id):
	board = Board.query.get((board_id, session_id))
    db.session.commit()
return make_response(json.dumps({ 'status': 'OK', 'board': board }, cls=CustomEncoder), 200)


@app.route('/bingo/sessions', methods=['POST'])
def create_session():
    dct = request.get_json(force=True)
    # name='Bingo', desc='A Bingo Session', private=False, max_players=16
    session = Session(dct["name"], dct["desc"], dct["private"], dct["max_players"])
    db.session.add(session)
    db.session.commit()
    return make_response(jsonify({'status': 'CREATED', 'uri': url_for('join_session', session_id=session.id)}), 201)


@app.route('/bingo/sessions/<int:session_id>', methods=['POST', 'PUT'])
def update_session(session_id):
    dct = request.get_json(force=True)
    session = Session.query.filter_by(id=session_id).update(dct)
    db.session.commit()
    return make_response(jsonify({'status': 'UPDATED', 'uri': url_for('join_session', session_id=session.id)}), 201)


@app.route('/bingo/sessions/<int:session_id>/boards', methods=['POST'])
def request_board(session_id):
    dct = request.get_json(force=True)
    session = Session.query.filter_by(id=session_id).first()
    plyr_cap = session.max_players
    plyr_num = session.cur_players+1
    if plyr_num > plyr_cap:
        return make_response(jsonify({'error': 'Game is Full'}), 409)

    board = Board(plyr_num, session.id)
    Session.query.filter_by(id=session_id).update({'cur_players': plyr_num})
    db.session.add(board)
    db.session.commit()
    return make_response(
		    jsonify({ 'status': 'CREATED', 'uri': url_for('retrieve_board', session_id=session.id, board_id=plyr_num) }),
		    201)


@app.route('/bingo/sessions/<int:session_id>/boards/<int:board_id>', methods=['DELETE'])
def leave_session(session_id, board_id):
    board = Board.query.filter_by(id=board_id, session_id=session_id).first()
    db.session.delete(board)
    db.session.commit()
    return make_response(jsonify({'status': 'DELETED'}), 204)


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)


@app.errorhandler(401)
def unauthorized(error):
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)


@app.errorhandler(403)
def forbidden(error):
    return make_response(jsonify({'error': 'Forbidden'}), 403)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(409)
def conflict(error):
    return make_response(jsonify({'error': 'Conflict'}), 409)

if __name__ == '__main__':
    # Uncomment on first run to setup the database schema
    db.create_all()
    app.run(debug=False)
