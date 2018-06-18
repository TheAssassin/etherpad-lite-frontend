import requests
import time
from datetime import datetime
from flask import (Flask, render_template, current_app, redirect, url_for,
                   request, session, flash, g, Markup, make_response)
from flask.ext.ldap3_login import LDAP3LoginManager
from flask.ext.ldap3_login.forms import LDAPLoginForm
from flask.ext.login import (LoginManager, UserMixin, login_required,
                             login_user, logout_user, current_user)
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.wtf import Form
from wtforms import PasswordField


app = Flask(__name__)

app.config.from_pyfile("defaults.py")
app.config.from_pyfile("../../../conf/eplitefrontend.py", silent=True)


from .epliteapi import (load_etherpad_settings,
                        get_etherpad_database_uri,
                        EtherpadLiteAPI)

load_etherpad_settings()

app.config.setdefault("SQLALCHEMY_BINDS", {})
app.config["SQLALCHEMY_BINDS"].update({
    "etherpad": get_etherpad_database_uri(),
})


if app.secret_key == None:
    msg = "Please configure a secret key in your local config file!"
    raise ValueError(msg)


manager = Manager(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

manager.add_command("db", MigrateCommand)

login_manager = LoginManager(app)
ldap_manager = LDAP3LoginManager(app)

login_manager.login_view = "login"
login_manager.login_message_category = "info"


# in the actual database this column is no primary key, but unfortunately
# SQLAlchemy accepty only tables that have a primary key column>
etherpad_store = db.Table("store",
    db.Column("key", db.Text(), primary_key=True),
    db.Column("value", db.Text()),
)


class AuthorizationError(Exception):
    pass


@app.errorhandler(AuthorizationError)
def handle_authorization_error(e):
    contact = current_app.config["CONTACT_EMAIL"]
    flash("You are not authorized to log in. Please contact %s for further "
          "information." % contact, "danger")
    return redirect(url_for("login"))


class EtherpadStore(db.Model):
    __bind_key__ = "etherpad"
    __table__ = etherpad_store


class User(UserMixin, db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    uid = db.Column(db.String(64), unique=True, nullable=False)
    display_name = db.Column(db.String(128), nullable=False)
    author_id = db.Column(db.String(32), nullable=True)


eplite = EtherpadLiteAPI()


def get_author_id(user):
    return eplite.call("createAuthorIfNotExistsFor",
                       name=user.display_name.encode("utf-8"),
                       authorMapper=user.id).json()["data"]["authorID"]


def get_group_id():
    if getattr(g, "group_id", None) is None:
        g.group_id = eplite.call("createGroupIfNotExistsFor",
                            groupMapper=1).json()["data"]["groupID"]
    return g.group_id


def create_ep_session(expiration):
    return eplite.call("createSession",
                       authorID=current_user.author_id,
                       groupID=get_group_id(),
                       validUntil=expiration.strftime("%s")
                       ).json()["data"]["sessionID"]


def build_pad_id(pad_name):
    return ("%s$%s" % (get_group_id(), pad_name))


def extract_pad_name(pad_id):
    return ("$".join(pad_id.split("$")[1:]))


app.jinja_env.globals["build_pad_name"] = build_pad_id
app.jinja_env.globals["extract_pad_name"] = extract_pad_name


def delete_ep_session(session_id):
    response = eplite.call("deleteSession", sessionID=session_id).json()
    if response["message"] == "ok":
        return True
    else:
        return False


@login_manager.user_loader
def user_loader(user_id):
    return User.query.get(user_id)


@ldap_manager.save_user
def save_user(dn, uid, data, memberships):
    uid = uid.lower()
    if uid not in current_app.config["AUTHORIZED_USERS"]:
        raise AuthorizationError()
    else:
        user = User.query.filter_by(uid=uid).first()
        if user is None:
            user = User(uid=uid)

        try:
            user.display_name = data["displayName"][0]
        except KeyError:
            user.display_name = uid

        if user.id is None:
            db.session.add(user)
            db.session.commit()

        user.author_id = get_author_id(user)
        db.session.add(user)
        db.session.commit()
        return user


def renew_ep_session(response):
    expiration = datetime.utcnow()
    expiration += current_app.config["PERMANENT_SESSION_LIFETIME"]
    ep_session_id = create_ep_session(expiration)
    session["ep_session_id"] = ep_session_id
    response.set_cookie("sessionID", ep_session_id, expires=expiration)
    return response


@app.errorhandler(requests.exceptions.ConnectionError)
def handle_connection_refused(e):
    html = render_template("connection_refused.html")
    rv = current_app.response_class(html, status=502)
    return rv


class ChangePasswordForm(Form):
    password = PasswordField("password")


class DeleteForm(Form):
    pass


class TogglePublicStatusForm(Form):
    pass


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LDAPLoginForm()

    if form.validate_on_submit():
        login_user(form.user)
        response = redirect(request.args.get("next", url_for("index")))
        renew_ep_session(response)
        return response

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    delete_ep_session(session["ep_session_id"])
    logout_user()
    response = redirect(request.args.get("next", url_for("index")))
    cookies = list(request.cookies.iterkeys())
    cookies.remove(current_app.config["SESSION_COOKIE_NAME"])
    for c in cookies:
        response.set_cookie(c, "", expires=0)
    return response


@app.route("/")
@login_required
def index():
    group_id = get_group_id()
    pad_ids = eplite.call("listPads", groupID=group_id).json()["data"]["padIDs"]
    pads = []
    for pad_id in pad_ids:
        pad_name = extract_pad_name(pad_id)
        pad_id = pad_id.encode("utf-8")

        args = [
            ("listAuthorsOfPad", dict(padID=pad_id)),
            ("getPublicStatus", dict(padID=pad_id)),
            ("isPasswordProtected", dict(padID=pad_id)),
            ("getLastEdited", dict(padID=pad_id)),
        ]

        responses = eplite.call_concurrent(args)
        author_ids = responses[0].json()["data"]["authorIDs"]
        pub_status = responses[1].json()["data"]["publicStatus"]
        is_pw_protected = responses[2].json()["data"]["isPasswordProtected"]
        last_edited = responses[3].json()["data"]["lastEdited"]
        authors = []
        for author_id in author_ids:
            author = User.query.filter_by(author_id=author_id).first()
            if author is not None:
                authors.append(author.display_name)

        pads.append((pad_id, pad_name, authors, pub_status, is_pw_protected,
                     datetime.fromtimestamp(last_edited // 1000)))

    pads.sort(key=lambda x: x[5], reverse=True)
    delete_form = DeleteForm()
    pw_form = ChangePasswordForm()
    tps_form = TogglePublicStatusForm()
    return render_template("index.html", pads=pads, delete_form=delete_form,
                           pw_form=pw_form, tps_form=tps_form)


@app.route("/pad/<pad_name>")
def view_pad(pad_name, fullscreen=False):
    form = LDAPLoginForm()
    pad_id = build_pad_id(pad_name).encode("utf-8")
    is_logged_in = current_user.is_authenticated()
    response = eplite.call("getPublicStatus", padID=pad_id).json()

    if response["message"] == "padID does not exist":
        return render_template("pad-not-found.html", pad_name=pad_name,
                               form=form), 404

    if not response["data"]["publicStatus"] and not is_logged_in:
        flash("This is a private pad. You likely need to login in order "
              "to access this pad.", "warning")
    pad_url = "/p/%s".encode('utf-8') % pad_id

    if fullscreen:
        template = "pad-fullscreen.html"
    else:
        template = "pad.html"
    response = make_response(
        render_template(template, pad_name=pad_name, pad_url=pad_url,
                        form=form)
    )

    if current_user.is_authenticated():
        renew_ep_session(response)
    return response


@app.route("/pad/<pad_name>/fullscreen")
def view_pad_fullscreen(pad_name):
    return view_pad(pad_name, fullscreen=True)


@app.route("/create", methods=["POST"])
@login_required
def create_pad():
    pad_name = request.form["pad_name"]
    pad_pw = request.form["pad_pw"]

    if pad_name is None:
        return current_app.response_class("pad_name required", status_code=400)
    elif "/" in pad_name:
        code = "<code>%s</code>" % pad_name
        flash(Markup("Pad name %s is invalid: <code>/</code> in pad name " \
                     "is not allowed!" % code), "danger")
        return redirect(url_for("index"))

    pad_name = pad_name.replace(" ", "_")

    response = eplite.call("createGroupPad", groupID=get_group_id(),
                           padName=pad_name.encode("utf-8")).json()

    if response["data"] is None:
        flash("Etherpad Lite error: %s" % response["message"],
              category="danger")
        return redirect(url_for("index"))
    else:
        pad_id = response["data"]["padID"].encode("utf-8")
        eplite.call("setPassword", padID=pad_id, password=pad_pw)
        time.sleep(0.5)
        flash("Successfully created pad %s!" % pad_name, "success")
        return redirect(url_for("view_pad",
                                pad_name=extract_pad_name(pad_id)))


@app.route("/change-password/<pad_name>", methods=["POST"])
@login_required
def change_password(pad_name):
    if current_user.uid not in current_app.config["ADMINS"]:
        raise AuthorizationError()
    form = ChangePasswordForm()
    if form.validate_on_submit():
        pad_id = build_pad_id(pad_name).encode("utf-8")
        eplite.call("setPassword", padID=pad_id, password=form.password.data)
        time.sleep(0.5)
        flash("Successfully deleted pad %s!" % pad_name,
              category="success")
        return redirect(url_for("index"))


@app.route("/toggle-public-status/<pad_name>", methods=["POST"])
@login_required
def toggle_public_status(pad_name):
    if current_user.uid not in current_app.config["ADMINS"]:
        raise AuthorizationError()
    form = TogglePublicStatusForm()
    if form.validate_on_submit():
        pad_id = build_pad_id(pad_name).encode("utf-8")
        r = eplite.call("getPublicStatus", padID=pad_id)
        status = str(not r.json()["data"]["publicStatus"]).lower()
        eplite.call("setPublicStatus", padID=pad_id, publicStatus=status)
        time.sleep(0.5)
        msg = "Successfully changed public status to %s for pad %s!" % \
            (status, pad_name)
        flash(msg, category="success")
        return redirect(url_for("index"))


@app.route("/delete/<pad_name>", methods=["POST"])
@login_required
def delete_pad(pad_name):
    if current_user.uid not in current_app.config["ADMINS"]:
        raise AuthorizationError()
    form = DeleteForm()
    if form.validate_on_submit():
        eplite.call("deletePad", padID=build_pad_id(pad_name).encode("utf-8"))
        # wait a small amount of time until the pad is really deleted
        time.sleep(0.5)
        flash("Successfully deleted pad %s!" % pad_name,
              category="success")
        return redirect(url_for("index"))
