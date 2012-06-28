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
        "index.html.tpl",
        link = "home"
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
        link = "projects",
        projects = projects
    )

@app.route("/projects/new", methods = ("GET",))
def new_project():
    return flask.render_template(
        "project_new.html.tpl",
        link = "new_project"
    )

@app.route("/projects", methods = ("POST",))
def create_project():
    # retrieves all the parameters from the request to be
    # handled then validated the required ones
    name = flask.request.form.get("name", None)
    description = flask.request.form.get("description", None)
    build_file = flask.request.files.get("build_file", None)
    days = int(flask.request.form.get("days", 0))
    hours = int(flask.request.form.get("hours", 0))
    minutes = int(flask.request.form.get("minutes", 0))
    seconds = int(flask.request.form.get("seconds", 0))

    # TODO: TENHO DE POR AKI O VALIDADOR !!!!

    # generates the unique identifier to be used to identify
    # the project reference and then uses it to create the
    # map describing the current project
    id = str(uuid.uuid4())
    project = {
        "id" : id,
        "name" : name,
        "description" : description,
        "recursion" : {
            "days" : days,
            "hours" : hours,
            "minutes" : minutes,
            "seconds" : seconds
        }
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
        project = project,
        link = "projects",
        sub_link = "info"
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
        project = project,
        link = "projects",
        sub_link = "edit"
    )

@app.route("/projects/<id>/edit", methods = ("POST",))
def update_project(id):
    # retrieves all the parameters from the request to be
    # handled then validated the required ones
    name = flask.request.form.get("name", None)
    description = flask.request.form.get("description", None)
    build_file = flask.request.files.get("build_file", None)
    days = int(flask.request.form.get("days", 0))
    hours = int(flask.request.form.get("hours", 0))
    minutes = int(flask.request.form.get("minutes", 0))
    seconds = int(flask.request.form.get("seconds", 0))

    # TODO: TENHO DE POR AKI O VALIDADOR !!!!

    project = {
        "id" : id,
        "name" : name,
        "description" : description,
        "recursion" : {
            "days" : days,
            "hours" : hours,
            "minutes" : minutes,
            "seconds" : seconds
        }
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
    # retrieves the "custom" run function to be used
    # as the work "callable", note that the schedule flag
    # is not set meaning that no schedule will be done
    # after the execution
    _run = _get_run(id, schedule = False)

    # inserts a new work task into the execution thread
    # for the current time, this way this task is going
    # to be executed immediately
    current_time = time.time()
    execution_thread.insert_work(current_time, _run)

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
        builds = builds,
        link = "projects",
        sub_link = "builds"
    )

@app.route("/projects/<id>/builds/<build_id>", methods = ("GET",))
def show_build(id, build_id):
    project = _get_project(id)
    build = _get_build(id, build_id)
    return flask.render_template(
        "build_show.html.tpl",
        project = project,
        build = build,
        link = "projects",
        sub_link = "info"
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
        log = log,
        link = "projects",
        sub_link = "log"
    )

@app.route("/projects/<id>/builds/<build_id>/files/", defaults = {"path" : "" }, methods = ("GET",))
@app.route("/projects/<id>/builds/<build_id>/files/<path:path>", methods = ("GET",))
def files_build(id, build_id, path = ""):
    project = _get_project(id)
    build = _get_build(id, build_id)

    file_path = _get_file_path(id, build_id, path)
    is_directory = os.path.isdir(file_path)
    if not is_directory: return flask.send_file(file_path)

    if path and not path.endswith("/"):
        return flask.redirect(
            flask.url_for("files_build", id = id, build_id = build_id, path = path + "/")
        )

    files = _get_build_files(id, build_id, path)
    return flask.render_template(
        "build_files.html.tpl",
        project = project,
        build = build,
        path = path,
        files = files,
        link = "projects",
        sub_link = "files"
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

    next_time = datetime.datetime.fromtimestamp(project["next_time"])
    project["_next_time"] = next_time.strftime("%b %d, %Y %H:%M:%S")

    return project

def _set_project(id, project):
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    project_path = os.path.join(project_folder, "description.json")
    project_file = open(project_path, "wb")
    try: json.dump(project, project_file)
    finally: project_file.close()

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

def _get_latest_build(id):
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    builds_folder = os.path.join(project_folder, "builds")
    build_ids = os.listdir(builds_folder)
    if not build_ids: return None
    build_ids.sort(reverse = True)
    build_id = build_ids[0]
    return _get_build(id, build_id)

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

def _get_file_path(id, build_id, path):
    path = path.strip("/")
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    builds_folder = os.path.join(project_folder, "builds")
    build_folder = os.path.join(builds_folder, build_id)
    full_path = os.path.join(build_folder, path)
    return full_path

def _touch_atm(id):
    project_folder = os.path.join(PROJECTS_FOLDER, id)
    file_path = os.path.join(project_folder, "build.atm")
    build_path = os.path.join(project_folder, "_build")
    if os.path.isdir(build_path): shutil.rmtree(build_path)
    os.makedirs(build_path)

    zip_file = zipfile.ZipFile(file_path, "r")
    zip_file.extractall(build_path)

def _get_recursion(project):
    recursion = project.get("recursion", {})
    days = recursion.get("days", 0)
    hours = recursion.get("hours", 0)
    minutes = recursion.get("minutes", 0)
    seconds = recursion.get("seconds", 0)

    return days * 86400\
        + hours * 3600\
        + minutes * 60\
        + seconds

def _get_run(id, schedule = False):
    def _run():
        initial_time = time.time()

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

        # retrieves the current associated project and build
        # and uses them to update the project structure with
        # the new value (then flushes the project contents)
        project = _get_project(id)
        build = _get_latest_build(id)
        project["result"] = build["result"]
        project["_result"] = build["_result"]
        project["build_time"] = build.get("delta", 0)
        project["builds"] = project.get("builds", 0) + 1
        _set_project(id, project)

        # in case schedule flag is not set, no need to
        # recalculate the new "next time" and put the
        # the new work into the scheduler, returns now
        if not schedule: return

        # retrieves the recursion integer value and uses
        # it to recalculate the next time value setting
        # then the value in the project value
        recursion = _get_recursion(project)
        next_time = initial_time + recursion
        project["next_time"] = next_time

        # re-saves the project because the next time value
        # has changed (flushes contents) then schedules the
        # project putting the work into the scheduler
        _set_project(id, project)
        _schedule_project(project)

    # returns the "custom" run function that contains a
    # transitive closure on the project identifier
    return _run

def _schedule_project(project):
    # retrieves the various required project attributes
    # for the scheduling process they are going to be used
    # in the scheduling process
    id = project["id"]
    next_time = project.get("next_time", time.time())

    # retrieves the "custom" run function to be used as the
    # work for the scheduler
    _run = _get_run(id, schedule = True)

    # inserts a new work task into the execution thread
    # for the next (target time)
    execution_thread.insert_work(next_time, _run)

if __name__ == "__main__":
    app.debug = True
    app.run(use_debugger = True, debug = True, use_reloader = False, host = "0.0.0.0")
    #app.run()
