import os


payload = (os.environ["POSTGRES_USER"],
           os.environ["POSTGRES_PASSWORD"],
           os.environ["POSTGRES_HOST"])
uri_template = "postgresql+psycopg2://%s:%s@%s:5432/eplitefrontend"
SQLALCHEMY_DATABASE_URI = uri_template % payload

SECRET_KEY = os.environ["SECRET_KEY"]


try:
    ADMINS = os.environ["ADMINS"].split(";")
except KeyError:
    pass

try:
    AUTHORIZED_USERS = os.environ["AUTHORIZED_USERS"].split(";")
except KeyError:
    pass

try:
    LDAP_HOST = os.environ["LDAP_HOST"]
except KeyError:
    pass


try:
    DEBUG = os.environ["DEBUG"]
except KeyError:
    pass
