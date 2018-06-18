#! /usr/bin/env python

from eplitefrontend import app, manager


if __name__ == "__main__":
    app.debug = True
    manager.run()

