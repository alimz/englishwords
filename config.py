import json


class Config:
    DEBUG = True
    DEVELOPMENT = True
    SECRET_KEY = 'EnglishWords024#$'
    SQLALCHEMY_DATABASE_URI = 'postgresql://DB_USER:DB_PASS@DB_HOST/DB_NAME'
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'json_serializer': lambda obj: json.dumps(obj, ensure_ascii=False)}
    JSON_AS_ASCII = False
    TRAP_HTTP_EXCEPTIONS = True
    PROJECT_ROOT = '/home/myuser/englishwords/source/'
    SEND_FILE_MAX_AGE_DEFAULT = 0


class ProductionConfig(Config):
    DEBUG = False
    DEVELOPMENT = False
    # DB_HOST = 'my.production.database'
