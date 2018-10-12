from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, SmallInteger, Unicode, Boolean, ForeignKey, Table
from sqlalchemy import Enum
from sqlalchemy.orm import relationship, backref
from sqlalchemy.exc import OperationalError

from app_enums import UserOptions, MediaType, LockingStatus, TorrentType

Base = declarative_base()

table_media_user_add = Table(
    'media_user_add',
    Base.metadata,
    Column('user_id', Integer, ForeignKey(u'users.id')),
    Column('media_id', Integer, ForeignKey(u'media.id'))
)


class User(Base):

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)

    name = Column(Unicode(200))
    last_name = Column(Unicode(200))
    nick_name = Column(Unicode(200), nullable=False)

    client_id = Column(Integer, nullable=False)

    media = relationship(
        'MediaData',
        secondary=table_media_user_add,
        primaryjoin=(table_media_user_add.c.user_id == id),
        backref=backref('users_add_media', lazy='dynamic'),
        lazy='dynamic',
        cascade="save-update, merge, delete")

    def __repr__(self):
        return '<User(name={0}, last_name={1}, nick_name={2}, client_id)>'.format(
            self.name,
            self.last_name,
            self.nick_name,
            self.client_id
        )


class UserOptionsT(Base):

    __tablename__ = 'user_options'

    id = Column(Integer, primary_key=True)

    option = Column(Enum(UserOptions), nullable=False)
    value = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    user = relationship('User', back_populates="options")

    def __repr__(self):
        return '<UserOption(user={0}, option={1}, value={2})>'.format(self.user_id, self.option, self.value)

User.options = relationship("UserOptionsT", order_by=UserOptionsT.id, back_populates="user")


class MediaData(Base):
    """
    Class for storing media data
    label - film label
    year - film year
    status - status of film finding
    """
    __tablename__ = u'media'
    id = Column(Integer, primary_key=True)
    label = Column(Unicode(400), nullable=False)
    year = Column(Integer, nullable=False)

    status = Column('status', Enum(LockingStatus), default=LockingStatus.IN_PROGRESS)

    type = Column(Enum(MediaType))

    download_url = Column(Unicode(400))
    theam_id = Column(Unicode(15))

    torrent_tracker = Enum(TorrentType)
    exsists_in_plex = Column(Boolean)

    kinopoisk_id = Column(Unicode(20))
    kinopoisk_url = Column(Unicode(400))

    __mapper_args__ = {
        'polymorphic_identity': MediaType.BASE_MEDIA,
        'polymorphic_on': type
    }


class Film(MediaData):
    """
    Class for storing film data
    label - film label
    year - film year
    status - status of film finding
    """
    __tablename__ = u'film'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, ForeignKey('media.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': MediaType.FILMS,
    }

    def __repr__(self):
        return u'<Film(label={0},year={1},kinopoisk_id={2}>'.format(
            self.label,
            self.year,
            self.kinopoisk_id
        )


class Serial(MediaData):
    """
    Class for storage serial data
    label - serial label
    season - number of season
    status - locking status
    series - number of series,  that have been already downloaded
    year - serial start year
    """

    __tablename__ = u'serial'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, ForeignKey('media.id'), primary_key=True)

    season = Column(SmallInteger, nullable=False, default=1)
    series = Column(SmallInteger, default=0)
    current_series = Column(SmallInteger, default=0)

    __mapper_args__ = {
        'polymorphic_identity': MediaType.SERIALS,
    }

    def __repr__(self):
        return u'<Serial(label={0},season={1},year={2},series={3},kinopoisk_id={4}>'.format(
            self.label,
            self.season,
            self.year,
            self.series,
            self.kinopoisk_id
        )


def test():
    """
    Run all tests

    :return:
    """
    s = create_test_env()

    test_user_env(s)
    test_serial_env(s)
    test_integreation_users_media(s)


def create_test_env():
    """
    Create test base im memory

    :return:
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    enj = create_engine('sqlite:///:memory:', echo=True)
    Base.metadata.create_all(enj)
    Session = sessionmaker(bind=enj)

    return Session()


def test_user_env(s):
    """
    Test user tabel and its options

    :param s:
    :return:
    """

    user = User(name='Alex', last_name='MP3', nick_name='Roll', client_id=1)

    option = UserOptionsT(option=UserOptions.NOTIFICATION, value=0)

    user.options.append(option)
    s.add(option)
    s.add(user)

    s.commit()

    alex = s.query(User).filter_by(name='Alex').first()

    result = s.query(User, UserOptionsT).\
                    filter(User.id==UserOptionsT.user_id).\
                    filter(UserOptionsT.option==UserOptions.NOTIFICATION).first()
    if result is not None:
        alex, opt = result
        print(opt)
        print(alex)


def test_serial_env(s):

    serial = Serial(label='RR', year=1999, season=1)

    film = Film(label='RrdddR', year=1999)

    s.add(serial)
    s.add(film)

    s.commit()

    film = s.query(Film).filter_by(label='RrdddR').first()
    print(film)

    serial = s.query(Serial).filter_by(label='RR').first()
    print(serial)


def test_integreation_users_media(s):

    serial = s.query(Serial).filter_by(label='RR').first()
    alex = s.query(User).filter_by(name='Alex').first()

    alex.media.append(serial)

    s.add(alex)
    s.commit()


def init_db(connection_str, db_name):
    from sqlalchemy import create_engine
    enj = create_engine(connection_str)
    enj.execute('USE {}'.format(db_name))
    Base.metadata.create_all(enj)
    return enj


def get_session(enj):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=enj)
    return Session()


def create_db(connection_str, db_name):
    from sqlalchemy import create_engine
    enj = create_engine(connection_str)
    enj.execute('CREATE DATABASE {}'.format(db_name))
    enj.execute('USE {}'.format(db_name))
    Base.metadata.create_all(enj)
    return enj

if __name__ == '__main__':

    test()


