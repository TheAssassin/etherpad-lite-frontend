import json
import os
import requests
import grequests
from collections import OrderedDict
from jsmin import jsmin
from urllib import urlencode
from .core import app


class ConfigurationError(ValueError):
    pass


class EtherpadLiteAPIError(Exception):
    def __init__(self, *args, **kwargs):
        self.response = kwargs.get("response", None)
        super(EtherpadLiteAPIError, self).__init__()


class EtherpadLiteAuthorizationError(EtherpadLiteAPIError):
    pass


def load_etherpad_settings():
    epdir = app.config["ETHERPAD_DIRECTORY"]
    settings_file = os.path.join(epdir, "settings.json")

    try:
        with open(settings_file, "r") as f:
            contents = f.read()
    except IOError:
        raise IOError("settings.json not found in ETHERPAD_DIRECTORY!")

    # run jsmin on file's contents to remove all comments
    settings = json.loads(jsmin(contents))

    if not settings["trustProxy"]:
        msg = "'trustProxy' set to false in your etherpad configuration! " + \
              "You need to set this to true so that proxying can work " + \
              "properly!"
        raise ConfigurationError(msg)

    if settings["port"] != 18002:
        msg = "nginx expects you to use port 18002! You need to change " + \
              "your etherpad configuration to use port 18002"
        raise ConfigurationError(msg)

    if settings["requireSession"]:
        msg = "You set 'requireSession' to true in your configuration, " + \
              "which prevents people from accessing your pads. Please " + \
              "set it to false!"
        raise ConfigurationError(msg)

    if settings["editOnly"] == False:
        msg = "Setting 'editOnly' to false in your etherpad " + \
              "configuration might have unexpected consequences! Please " + \
              "set it to true!"
        raise ConfigurationError(msg)

    # use jsmin to filter comments
    app.config["ETHERPAD_SETTINGS"] = settings


def get_etherpad_database_uri():
    epdir = app.config["ETHERPAD_DIRECTORY"]
    settings = app.config["ETHERPAD_SETTINGS"]
    dbtype = settings["dbType"]
    if dbtype == "dirty":
        raise ValueError("dirty database not supported! Please use " + \
                         "either postgres, mysql or sqlite!")
    elif dbtype == "sqlite":
        filename = settings["dbSettings"]["filename"]
        return "sqlite:///" + os.path.join(epdir, filename)
    else:
        if dbtype == "postgres":
            dbtype = "postgresql"
        dbsettings = settings["dbSettings"]
        user = dbsettings["user"]
        password = dbsettings["password"]
        host = dbsettings["host"]
        database = dbsettings["database"]
        return "%s://%s:%s@%s/%s" % (dbtype, user, password, host, database)


class EtherpadLiteAPI(object):
    apiversion = 1

    def __init__(self, address=None):
        if address is None:
            settings = app.config["ETHERPAD_SETTINGS"]
            ip = settings["ip"]
            if ip != "127.0.0.1":
                print "settings.json: don't use any other ip but " + \
                      "127.0.0.1 in production (current value: %s)" % ip
            port = settings["port"]
            self.address = "http://%s:%s" % (ip, port)
        else:
            if address.endswith("/"):
                self.address = address[:-1]
            else:
                self.address = address

        epdir = app.config["ETHERPAD_DIRECTORY"]
        keyfile = os.path.join(epdir, "APIKEY.txt")
        self.apikey = open(keyfile).read()

        self.session = requests.session()

    def build_url(self, path):
        if not path.startswith("/"):
            raise ValueError("path has to start with '/'")
        return self.address + path

    def get(self, path):
        url = self.build_url(path)
        return self.session.get(url)

    def build_path(self, functionname, **kwargs):
        kwargs.pop("apikey", None)
        args = OrderedDict()
        args["apikey"] = self.apikey
        args.update(kwargs)
        qs = urlencode(args)
        return "/api/%d/%s?%s" % (self.apiversion, functionname, qs)

    def get_concurrent(self, paths):
        reqs = []
        for path in paths:
            url = self.build_url(path)
            req = grequests.get(url)
            reqs.append(req)
        return grequests.map(reqs)

    def call_concurrent(self, args):
        paths = [self.build_path(i[0], **i[1]) for i in args]
        responses = self.get_concurrent(paths)

        for response in responses:
            if response.status_code != 200:
                if response.status_code == 401:
                    raise EtherpadLiteAuthorizationError(response=response)
                raise EtherpadLiteAPIError(response=response)

        return responses

    def call(self, function_name, **kwargs):
        response = self.get(self.build_path(function_name, **kwargs))

        if response.status_code != 200:
            if response.status_code == 401:
                raise EtherpadLiteAuthorizationError(response=response)
            raise EtherpadLiteAPIError(response=response)

        return response
