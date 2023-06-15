from app import db


class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class User(BaseModel):
    __tablename__ = 'users'

    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime(), default=db.func.current_timestamp())


class Word(BaseModel):
    __tablename__ = 'words'

    word_en = db.Column(db.String(15), nullable=True)
    word_fa = db.Column(db.String(82), nullable=True)
    pron = db.Column(db.String(25), nullable=True)
    dsc_en = db.Column(db.String(89), nullable=True)
    book_id = db.Column(db.SMALLINT, nullable=True)
    unit_id = db.Column(db.SMALLINT, nullable=True)
    marked_w = db.Column(db.SMALLINT, nullable=True)
    num_sound = db.Column(db.SMALLINT, nullable=True)
    exam_en = db.Column(db.TEXT, nullable=False)
    exam_fa = db.Column(db.TEXT, nullable=False)


class Magnet(BaseModel):
    __tablename__ = 'magnets'

    word_id = db.Column(db.ForeignKey('words.id'))
    user_id = db.Column(db.ForeignKey('users.id'))
    fetch = db.Column(db.SMALLINT, default=0)
    selected = db.Column(db.SMALLINT, default=1)
    timestamp = db.Column(db.DateTime(), default=db.func.current_timestamp())


class MagnetHistoryStatus(BaseModel):
    __tablename__ = 'magnet_history_status'

    title = db.Column(db.String(20), nullable=False)


class MagnetHistory(BaseModel):
    __tablename__ = 'magnet_histories'

    magnet_id = db.Column(db.ForeignKey('magnets.id'))
    status_id = db.Column(db.ForeignKey('magnet_history_status.id'))
    timestamp = db.Column(db.DateTime(), default=db.func.current_timestamp())
