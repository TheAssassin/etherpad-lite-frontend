import os
from datetime import timedelta

epdir = os.path.join(os.path.dirname(__file__), "..", "..", "etherpad-lite")
ETHERPAD_DIRECTORY = os.path.abspath(epdir)

dbpath = os.path.join(os.path.dirname(__file__), "..", "main.db")
SQLALCHEMY_DATABASE_URI = "sqlite:///" + dbpath

SITE_NAME = "Etherpad Lite"

ADMINS = []

LDAP_HOST = "ldap://127.0.0.1:389"
LDAP_BASE_DN = "dc=example,dc=com"
LDAP_USER_DN = "ou=Users"
LDAP_USER_RDN_ATTR = "uid"
LDAP_USER_LOGIN_ATTR = "uid"
LDAP_SEARCH_FOR_GROUPS = False
LDAP_BIND_USER_DN = None
LDAP_BIND_USER_PASSWORD = None
LDAP_ALWAYS_SEARCH_BIND = True

PERMANENT_SESSION_LIFETIME = timedelta(days=7)

AUTHORIZED_USERS = []

CONTACT_EMAIL = "info@example.com"
