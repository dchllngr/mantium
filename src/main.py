#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Automium System
# Copyright (C) 2008 Hive Solutions Lda.
#
# This file is part of Hive Automium System.
#
# Hive Automium System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Automium System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Automium System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision: 9712 $"
""" The revision number of the module """

__date__ = "$LastChangedDate: 2010-08-10 13:42:37 +0100 (ter, 10 Ago 2010) $"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import os
import uuid
import json
import time
import flask
import shutil
import zipfile
import automium
import datetime

import execution

CURRENT_DIRECTORY = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(CURRENT_DIRECTORY, "uploads")
PROJECTS_FOLDER = os.path.join(CURRENT_DIRECTORY, "projects")
ALLOWED_EXTENSIONS = set(["txt", "pdf", "png", "jpg", "jpeg", "gif"])

app = flask.Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 1024 ** 3

execution_thread = execution.ExecutionThread()
execution_thread.start()

@app.route("/")
@app.route("/index")
def index():
    return flask.render_template(
        "index.html.tpl"
    )

@app.route("/login", methods = ("GET",))
def login():
    return flask.render_template(
        "login.html.tpl"
    )

@app.route("/login", methods = ("POST",))
def do_login():
    return flask.request.form["username"]

@app.route("/projects", methods = ("GET",))
def projects():
    # retrieves the various entries from the projects
    # folder as the various projects
    projects = _get_projects()
    return flask.render_template(
        "project_list.html.tpl",
        projects = projects
    )

@app.route("/projects/new", methods = ("GET",))
def new_project():
    return flask.render_template(
        "project_new.html.tpl"
    )

@app.route("/projects", methods = ("POST",))
def create_project():
    # retrieves all the parameters from the request to be
    # handled then validated the required ones
    name = flask.request.form.get("name", None)
    description = flask.request.form.get("description", None)
    build_file = flask.request.files.get("build_file", None)

    # TODO: TENHO DE POR AKI O VALIDADOR !!!!

    # generates the unique identifier to be used to identify
    # the project reference and then uses it to create the
    # map describing the current project
    id = str(uuid.uuid4())
    project = {
        "id" : id,
        "name" : name,
        "description" : description
    }

    # creates the path to the project folder and creates it
    # in case its required then creates the path to the description
    # file of the project and dumps the json describing the project
    # into such file for latter reference
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    if not os.path.isdir(project_folder): os.makedirs(project_folder)
    project_path = os.path.join(project_folder, "description.json")
    project_file = open(project_path, "wb")
    try: json.dump(project, project_file)
    finally: project_file.close()

    # saves the build file in the appropriate location
    # folder for latter usage
    file_path = os.path.join(project_folder, "build.atm")
    build_file.save(file_path)

    # touches the automium file so that its contents are
    # correctly deployed into the build directory
    _touch_atm(id)

    # ensures that the builds folder exists in order to avoid
    # any possible listing problem
    builds_folder = os.path.join(project_folder, "builds")
    os.makedirs(builds_folder)

    return flask.redirect(
        flask.url_for("show_project", id = id)
    )

@app.route("/projects/<id>", methods = ("GET",))
def show_project(id):
    project = _get_project(id)
    return flask.render_template(
        "project_show.html.tpl",
        project = project
    )

@app.route("/projects/<id>/edit", methods = ("GET",))
def edit_project(id):
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    project_path = os.path.join(project_folder, "description.json")
    project_file = open(project_path, "rb")
    try: project = json.load(project_file)
    finally: project_file.close()
    return flask.render_template(
        "project_edit.html.tpl",
        project = project
    )

@app.route("/projects/<id>/edit", methods = ("POST",))
def update_project(id):
    # retrieves all the parameters from the request to be
    # handled then validated the required ones
    name = flask.request.form.get("name", None)
    description = flask.request.form.get("description", None)
    build_file = flask.request.files.get("build_file", None)

    # TODO: TENHO DE POR AKI O VALIDADOR !!!!

    project = {
        "id" : id,
        "name" : name,
        "description" : description
    }

    # creates the path to the project folder and creates it
    # in case its required then creates the path to the description
    # file of the project and dumps the json describing the project
    # into such file for latter reference
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    if not os.path.isdir(project_folder): os.makedirs(project_folder)
    project_path = os.path.join(project_folder, "description.json")
    project_file = open(project_path, "wb")
    try: json.dump(project, project_file)
    finally: project_file.close()

    # in case the build file was provided must handle it correctly
    # should be processed
    if build_file:
        # saves the build file in the appropriate location
        # folder for latter usage
        file_path = os.path.join(project_folder, "build.atm")
        build_file.save(file_path)

        # touches the automium file so that its contents are
        # correctly deployed into the build directory
        _touch_atm(id);

    return flask.redirect(
        flask.url_for("show_project", id = id)
    )

@app.route("/projects/<id>/delete", methods = ("GET", "POST"))
def delete_project(id):
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    if os.path.isdir(project_folder): shutil.rmtree(project_folder)
    return flask.redirect(
        flask.url_for("projects")
    )

@app.route("/projects/<id>/run")
def run_project(id):
    def _run():
        project_folder = os.path.join(PROJECTS_FOLDER, id)
        build_path = os.path.join(project_folder, "_build")
        _build_path = os.path.join(build_path, "build.json")

        build_file = open(_build_path, "rb")
        try: configuration = json.load(build_file)
        finally: build_file.close()

        current = os.getcwd()
        os.chdir(project_folder)
        try: automium.run(build_path, configuration)
        finally: os.chdir(current)

    execution_thread.insert_work(time.time(), _run)

    return flask.redirect(
        flask.url_for("show_project", id = id)
    )

@app.route("/projects/<id>/builds")
def builds(id):
    project = _get_project(id)
    builds = _get_builds(id)
    return flask.render_template(
        "build_list.html.tpl",
        project = project,
        builds = builds
    )

@app.route("/projects/<id>/builds/<build_id>", methods = ("GET",))
def show_build(id, build_id):
    project = _get_project(id)
    build = _get_build(id, build_id)
    return flask.render_template(
        "build_show.html.tpl",
        project = project,
        build = build
    )

@app.route("/projects/<id>/builds/<build_id>/delete", methods = ("GET", "POST"))
def delete_build(id, build_id):
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    builds_folder = os.path.join(project_folder, "builds")
    build_folder = os.path.join(builds_folder, build_id)
    if os.path.isdir(build_folder): shutil.rmtree(build_folder)
    return flask.redirect(
        flask.url_for("builds", id = id)
    )

@app.route("/projects/<id>/builds/<build_id>/log", methods = ("GET",))
def log_build(id, build_id):
    project = _get_project(id)
    build = _get_build(id, build_id)
    log = _get_build_log(id, build_id)
    return flask.render_template(
        "build_log.html.tpl",
        project = project,
        build = build,
        log = log
    )

@app.route("/projects/<id>/builds/<build_id>/files/", defaults = {"path" : "" }, methods = ("GET",))
@app.route("/projects/<id>/builds/<build_id>/files/<path:path>", methods = ("GET",))
def files_build(id, build_id, path = ""):
    project = _get_project(id)
    build = _get_build(id, build_id)
    files = _get_build_files(id, build_id, path)
    return flask.render_template(
        "build_files.html.tpl",
        project = project,
        build = build,
        path = path,
        files = files
    )

@app.route("/status")
def status():
    return "this is a status page"

@app.errorhandler(404)
def handler_404(error):
    return str(error)

@app.errorhandler(413)
def handler_413(error):
    return str(error)

def _get_projects():
    projects = []
    ids = os.listdir(PROJECTS_FOLDER)
    for id in ids:
        path = os.path.join(PROJECTS_FOLDER, id)
        if not os.path.isdir(path): continue
        project = _get_project(id)
        projects.append(project)
    return projects

def _get_builds(id):
    builds = []
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    builds_folder = os.path.join(project_folder, "builds")
    build_ids = os.listdir(builds_folder)
    for build_id in build_ids:
        path = os.path.join(builds_folder, build_id)
        if not os.path.isdir(path): continue
        build = _get_build(id, build_id)
        builds.append(build)
    return builds

def _get_project(id):
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    project_path = os.path.join(project_folder, "description.json")
    project_file = open(project_path, "rb")
    try: project = json.load(project_file)
    finally: project_file.close()
    return project

def _get_build(id, build_id):
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    builds_folder = os.path.join(project_folder, "builds")
    build_folder = os.path.join(builds_folder, build_id)
    build_path = os.path.join(build_folder, "description.json")
    build_file = open(build_path, "rb")
    try: build = json.load(build_file)
    finally: build_file.close()

    result = build["result"]
    start_time = datetime.datetime.fromtimestamp(build["start_time"])
    end_time = datetime.datetime.fromtimestamp(build["end_time"])
    build["_result"] = result and "passed" or "failed"
    build["_start_time"] = start_time.strftime("%b %d, %Y %H:%M:%S")
    build["_end_time"] = end_time.strftime("%b %d, %Y %H:%M:%S")

    return build

def _get_build_log(id, build_id):
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    builds_folder = os.path.join(project_folder, "builds")
    build_folder = os.path.join(builds_folder, build_id)
    log_path = os.path.join(build_folder, "log/automium.log")
    log_file = open(log_path, "rb")
    try: log = log_file.read()
    finally: log_file.close()

    return log

def _get_build_files(id, build_id, path = ""):
    path = path.strip("/")
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    builds_folder = os.path.join(project_folder, "builds")
    build_folder = os.path.join(builds_folder, build_id)
    full_path = os.path.join(build_folder, path)
    entries = os.listdir(full_path)
    path and entries.insert(0, "..")
    return entries

def _touch_atm(id):
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    file_path = os.path.join(project_folder, "build.atm")
    build_path = os.path.join(project_folder, "_build")
    if os.path.isdir(build_path): shutil.rmtree(build_path)
    os.makedirs(build_path)

    zip_file = zipfile.ZipFile(file_path, "r")
    zip_file.extractall(build_path)

if __name__ == "__main__":
    app.debug = True
    app.run(use_debugger = True, debug = True, use_reloader = False, host = "0.0.0.0")
    #app.run()
