from peewee import MySQLDatabase, Model, CharField, DateTimeField, TextField
import datetime

db = MySQLDatabase(
    'data_db',
    user='db_user',
    password='db_password',
    host='localhost',
    port=3306)


class BaseModel(Model):
    class Meta:
        database = db

        indexes = (
            (('id_in_source'), False),
        )

    @classmethod
    def recordExists(cls, id_in_source):
        return cls.select().where(cls.id_in_source == id_in_source).exists()


class Post(BaseModel):
    source = CharField(default='')
    title = CharField(default='', max_length=1000)
    desc = TextField(default='')
    date = DateTimeField(default=datetime.datetime.now)
    id_in_source = CharField(default='')
    created_time = DateTimeField(default=datetime.datetime.now)
