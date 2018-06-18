
# Etherpad Lite Frontend (EPF)

## Introduction

The software Etherpad Lite Frontend tries to provide a frontend similar to
PiratenPad. It is a combination of Etherpad Lite, the Etherpad Lite Frontend
Python software and the NGINX webserver which routes the requests to these
two backends.

The Python software supervisord will be used to manage all the processes of
the bundled software. IT will take care of automatically starting, restarting
processes and logging their output.

The software was initially developed for use by a German students council.
It requires a working LDAP setup for authentication. If you need another kind
of authentication system, feel free to implement it and please consider
contributing it upstream as well by sending a PR!


## Warning

This software has initially been developed in 2015 and 2016 and has been
running fine since then. Please expect issues when trying out this software!

The software components are probably outdated. You may consider upgrading to
newer versions of the components.

Nowadays, I'd also rather split up Etherpad Lite, PostgreSQL and the frontend
into three separate containers.

**PRs welcome!**


## License

See `LICENSE`.


## Etherpad Lite Frontend Python software

The Etherpad Lite Frontend Python software uses the HTTP REST API provided by
Etherpad Lite. Since it uses the group pad API, almost all of Etherpad Lite's
functionality can be used.

See https://github.com/ether/etherpad-lite/wiki/HTTP-API for more information.


## Run EPF with Docker-Compose (a.k.a. the easy way)

Probably the easiest way to run EPF is to use Docker containers managed by
Docker Compose.

First of all, copy `docker-compose.yml.example` to `docker-compose.yml`. This
file contains the configuration of the containers that should be managed by
Docker Compose.

The basic settings are configured already, but a few values have to be
adjusted. Docker containers are usually configured using environment
variables, which are listed in the `environment:` section.

The first setting you must change is the `POSTGRES_PASSWORD`. This should be
set to a unique random value. Use a tool like `pwgen` to generate a suitable
one. Do the same with the `SECRET_KEY` setting.

By default the database and application data is stored in the directory
`docker-data` in the repository directory. You could also change its path, but
make sure you don't delete (and ideally backup) the directory.

You should not touch `POSTGRES_USER` and `POSTGRES_HOST` as external
PostgreSQL servers are explicitly not supported.

You will probably have to change the LDAP server related settings. By default
a server on the Docker host would be used, but it is rather unlikely that
this works on any other system than the ones used for development.

Only a limited subset of configuration keys can currently be specified as
environment variables to the Docker container:

| Variable name       | description                                                                 | usage example                               |
|---------------------|-----------------------------------------------------------------------------|---------------------------------------      |
| `POSTGRES_HOST`     | PostgreSQL database hostname                                                | `POSTGRES_HOST: "postgres"`                  |
| `POSTGRES_USER`     | PostgreSQL database username                                                | `POSTGRES_USER: "epf"`                       |
| `POSTGRES_PASSWORD` | PostgreSQL database password                                                | `POSTGRES_PASSWORD: "secure password"`       |
| `ADMINS`            | users to grant admin privileges to (separated by semicolons)                | `ADMINS: "user1;user2;user3"`                |
| `AUTHORIZED_USERS`  | users who may log into EPF (separated by semicolons)                        | `AUTHORIZED_USERS: "user1;user2"`            |
| `LDAP_HOST`         | hostname or connection string) of the LDAP server to use for authentication | `LDAP_HOST: "ldap://ldap.mycompany.tld:389"` |
| `LDAP_BASE_DN`      | Base DN to search users in                                                  | `LDAP_BASE_DN: "dc=example,dc=com"`          |
| `LDAP_USER_DN`      | DN relative to `LDAP_BASE_DN` to search users in                            | `LDAP_USER_DN: "cn=users"`                   |
| `DEBUG`             | Switch on debug mode (not useful in production)                             | `DEBUG=1`                                   |

If you want to use other configuration keys, as shown in the section
"Configure Etherpad Lite Frontend", you need to mount a configuration file
on the Docker host using the flag `-v`. Copy the Docker default configuration
file in `docker/conf/eplitefrontend.py` to a directory on your host (in the
following example `./docker-data/eplitefrontend.py`) and add the following to
your `docker-compose.yml`:

    [...]
    epf:
      [...]
      volumes:
        - [...]
        - "./docker-data/eplitefrontend.py:/srv/eplitefrontend/conf/eplitefrontend.py"

If you keep the code that sets PostgreSQL settings and the secret key, you
won't have to change the rest of `docker-compose.yml`, otherwise you will have
to copy over these settings manually into `./docker-data/eplitefrontend.py`.


### Control Docker containers using Docker Compose

In order to start EPF, you need to start both your PostgreSQL container and
the EPF application container:

    docker-compose up -d

In order to stop the Docker containers, run the following command and wait for
its completion:

    docker-compose stop

This allows the software in the application container to finish any operations
on the database.

For further information about how to use Docker Compose, see
http://54.71.194.30:4018/compose/.


### Install Etherpad Lite plugins

To install additional Etherpad Lite plugins, run the following commands:

    docker-compose exec epf /bin/bash -c "(cd lib/etherpad-lite && npm install ep_<plugin>)"
    docker-compose restart epf



## Run EPF without Docker

### Installation

_This is a setup guide for Debian/Ubuntu. This method is a lot more difficult
and should not be used by unexperienced users. Please consider using the
method above instead._

To install EPF, clone this repository, preferrably to `/srv/pad`, because
this path will be used in the following tutorial.

You might want to create a separate user for this software. To do this, run

    sudo adduser --system --group --disabled-login --disabled-password \
    --shell /bin/false --home /srv/pad pad

You will need to get copies of Etherpad Lite and NGINX in order to use this
software. Both repositories were added as submodules to make sure you install
the correct version. Just run `git submodule update --init` in the root
directory of your Git repository.

You will need to install some Python packages which EPF depends on. The
cleanest approach is using a virtual Python environment. There are basically
two approaches to do this: Manually create a virtual environment or use the
`virtualenvwrapper` helper tool.

1. Manually install virtual environment
   - Install `virtualenv`: `sudo apt-get install python-virtualenv`
   - Create a virtual environment: `virtualenv padenv`
   - Activate your virtual environment: `. padenv/bin/activate`
   - Install the dependencies: `pip install -r requirements.txt`

1. Use `virtualenvwrapper`
   - Create a virtual environment: `mkvirtualenv pad`
   - (to later activate this environment again, run `workon pad`)
   - Install the dependencies: `pip install -r requirements.txt`

The run scripts in the `bin/` directory will automatically install
dependencies and compile the software before running it. Therefore you should
run `bin/run-nginx` and `bin/run-etherpad-lite` once before running
supervisord.

After the first run of Etherpad Lite, an empty config will be created. You
should adjust a few settings to improve your pads' security. Apart from this
many people prefer to change the default behaviour of Etherpad Lite, too
(e.g. to always show the chat).

The config will be created in `lib/etherpad-lite/settings.json`.

Running `bin/manage-frontend` will inform you about configuration problems.
Just run `bin/manage-frontend` until it will print the normal help text on
your console.

Don't forget you need to configure a database for EPF's Python part. The
SQLAlchemy library is used to handle database connections.
The preconfigured SQLite database should be fine for a small user base.
You can also configure a database in any other DBM that SQLAlchemy supports.
See http://pythonhosted.org/Flask-SQLAlchemy/config.html#connection-uri-format
for further information. (Don't forget to install the database drivers in your
virtual environment.)

### Configure Etherpad Lite Frontend

You will also have to configure EPF in order to be able to run it. The script
`bin/manage-frontend` will also inform you about what settings are incorrect
or missing.

The Etherpad Lite Frontend software can be configured in the file
`conf/eplitefrontend.py`.

The important configuration keys are:

1. `SECRET_KEY`: Sessions will be encrypted with this key which improves
   security. You should send this to a random string.
   See http://flask.pocoo.org/docs/0.10/quickstart/#sessions for further
   information how to generate good keys.

1. `AUTHORIZED_USERS`: This is a list of user IDs that can log into EPF.
   An empty list means that noone will be able to log in. Since the config
   file is just a normal Python file, you can also generate this list.

1. `ADMINS`: This list specifies what users can perform dangerous changes
   (like for example deleting pads). An empty list means noone can perform
   any dangerous changes.

1. `LDAP_*`: You will want to configure your LDAP authentication. EPF uses
   the Flask extension `flask-ldap3-login` to handle LDAP connections.
   You can read about its configuration here:
   http://flask-ldap3-login.readthedocs.org/en/latest/configuration.html

If you can run `bin/manage-frontend` without any errors, you're usually
good to go.

### Run EPF

The recommended way to run EPF and its components is to run `supervisord`.
A script for this is included in the software distribution:
`bin/run-supervisord`.

You can also install an `upstart` job to automatically run EPF when your
system boots.

Create the file `/etc/init/pad.conf` with the following contents:

    description     "etherpad lite frontend"

    start on runlevel [2345]
    stop on runlevel [!2345]

    respawn
    respawn limit 10 5

    setuid in-pad

    script
        # use this if you manually created a virtualenv
        . /srv/in-pad/padenv/bin/activate
        # use this if you used virtualenvwrapper
        #. /srv/in-pad/.virtualenvs/pad/bin/activate
        cd /srv/in-pad/etherpad-lite-frontend
        exec bin/run-supervisord
    end script

You just have to adjust the virtual environment settings.

Now you can run the following (self-explaining) commands:

- `start in-pad`
- `stop in-pad`
- `restart in-pad`
- `status in-pad`

### Install Etherpad Lite plugins

Just `cd` into `/srv/pad/etherpad-lite-frontend/lib/etherpad-lite` and run
`npm install ep_<plugin>`.
