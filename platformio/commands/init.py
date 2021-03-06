# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=too-many-arguments,too-many-locals, too-many-branches

from os import getcwd, makedirs
from os.path import isdir, isfile, join
from shutil import copyfile

import click

from platformio import exception, util
from platformio.commands.platform import \
    platform_install as cli_platform_install
from platformio.ide.projectgenerator import ProjectGenerator
from platformio.managers.platform import PlatformManager


def validate_boards(ctx, param, value):  # pylint: disable=W0613
    pm = PlatformManager()
    for id_ in value:
        try:
            pm.board_config(id_)
        except exception.UnknownBoard:
            raise click.BadParameter(
                "`%s`. Please search for board ID using `platformio boards` "
                "command" % id_)
    return value


@click.command(
    "init", short_help="Initialize PlatformIO project or update existing")
@click.option(
    "--project-dir",
    "-d",
    default=getcwd,
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True))
@click.option(
    "-b", "--board", multiple=True, metavar="ID", callback=validate_boards)
@click.option(
    "--ide", type=click.Choice(ProjectGenerator.get_supported_ides()))
@click.option("-O", "--project-option", multiple=True)
@click.option("--env-prefix", default="")
@click.pass_context
def cli(
        ctx,  # pylint: disable=R0913
        project_dir,
        board,
        ide,
        project_option,
        env_prefix):

    if project_dir == getcwd():
        click.secho("\nThe current working directory", fg="yellow", nl=False)
        click.secho(" %s " % project_dir, fg="cyan", nl=False)
        click.secho(
            "will be used for project.\n"
            "You can specify another project directory via\n"
            "`platformio init -d %PATH_TO_THE_PROJECT_DIR%` command.",
            fg="yellow")
        click.echo("")

    click.echo("The next files/directories have been created in %s" %
               click.style(
                   project_dir, fg="cyan"))
    click.echo("%s - Project Configuration File" % click.style(
        "platformio.ini", fg="cyan"))
    click.echo("%s - Put your source files here" % click.style(
        "src", fg="cyan"))
    click.echo("%s - Put here project specific (private) libraries" %
               click.style(
                   "lib", fg="cyan"))

    init_base_project(project_dir)

    if board:
        fill_project_envs(ctx, project_dir, board, project_option, env_prefix,
                          ide is not None)

    if ide:
        if not board:
            board = get_first_board(project_dir)
            if board:
                board = [board]
        if not board:
            raise exception.BoardNotDefined()
        if len(board) > 1:
            click.secho(
                "Warning! You have initialised project with more than 1 board"
                " for the specified IDE.\n"
                "However, the IDE features (code autocompletion, syntax "
                "linter) have been configured for the first board '%s' from "
                "your list '%s'." % (board[0], ", ".join(board)),
                fg="yellow")
        pg = ProjectGenerator(project_dir, ide, board[0])
        pg.generate()

    click.secho(
        "\nProject has been successfully initialized!\nUseful commands:\n"
        "`platformio run` - process/build project from the current "
        "directory\n"
        "`platformio run --target upload` or `platformio run -t upload` "
        "- upload firmware to embedded board\n"
        "`platformio run --target clean` - clean project (remove compiled "
        "files)\n"
        "`platformio run --help` - additional information",
        fg="green")


def get_first_board(project_dir):
    config = util.load_project_config(project_dir)
    for section in config.sections():
        if not section.startswith("env:"):
            continue
        elif config.has_option(section, "board"):
            return config.get(section, "board")
    return None


def init_base_project(project_dir):
    if not util.is_platformio_project(project_dir):
        copyfile(
            join(util.get_source_dir(), "projectconftpl.ini"),
            join(project_dir, "platformio.ini"))

    lib_dir = join(project_dir, "lib")
    src_dir = join(project_dir, "src")
    config = util.load_project_config(project_dir)
    if config.has_option("platformio", "src_dir"):
        src_dir = join(project_dir, config.get("platformio", "src_dir"))

    for d in (src_dir, lib_dir):
        if not isdir(d):
            makedirs(d)

    init_lib_readme(lib_dir)
    init_ci_conf(project_dir)
    init_cvs_ignore(project_dir)


def init_lib_readme(lib_dir):
    if isfile(join(lib_dir, "readme.txt")):
        return
    with open(join(lib_dir, "readme.txt"), "w") as f:
        f.write("""
This directory is intended for the project specific (private) libraries.
PlatformIO will compile them to static libraries and link to executable file.

The source code of each library should be placed in separate directory, like
"lib/private_lib/[here are source files]".

For example, see how can be organized `Foo` and `Bar` libraries:

|--lib
|  |--Bar
|  |  |--docs
|  |  |--examples
|  |  |--src
|  |     |- Bar.c
|  |     |- Bar.h
|  |--Foo
|  |  |- Foo.c
|  |  |- Foo.h
|  |- readme.txt --> THIS FILE
|- platformio.ini
|--src
   |- main.c

Then in `src/main.c` you should use:

#include <Foo.h>
#include <Bar.h>

// rest H/C/CPP code

PlatformIO will find your libraries automatically, configure preprocessor's
include paths and build them.

More information about PlatformIO Library Dependency Finder
- http://docs.platformio.org/en/stable/librarymanager/ldf.html
""")


def init_ci_conf(project_dir):
    if isfile(join(project_dir, ".travis.yml")):
        return
    with open(join(project_dir, ".travis.yml"), "w") as f:
        f.write("""# Continuous Integration (CI) is the practice, in software
# engineering, of merging all developer working copies with a shared mainline
# several times a day < http://docs.platformio.org/en/stable/ci/index.html >
#
# Documentation:
#
# * Travis CI Embedded Builds with PlatformIO
#   < https://docs.travis-ci.com/user/integration/platformio/ >
#
# * PlatformIO integration with Travis CI
#   < http://docs.platformio.org/en/stable/ci/travis.html >
#
# * User Guide for `platformio ci` command
#   < http://docs.platformio.org/en/stable/userguide/cmd_ci.html >
#
#
# Please choice one of the following templates (proposed below) and uncomment
# it (remove "# " before each line) or use own configuration according to the
# Travis CI documentation (see above).
#


#
# Template #1: General project. Test it using existing `platformio.ini`.
#

# language: python
# python:
#     - "2.7"
#
# sudo: false
# cache:
#     directories:
#         - "~/.platformio"
#
# install:
#     - pip install -U platformio
#
# script:
#     - platformio run


#
# Template #2: The project is intended to by used as a library with examples
#

# language: python
# python:
#     - "2.7"
#
# sudo: false
# cache:
#     directories:
#         - "~/.platformio"
#
# env:
#     - PLATFORMIO_CI_SRC=path/to/test/file.c
#     - PLATFORMIO_CI_SRC=examples/file.ino
#     - PLATFORMIO_CI_SRC=path/to/test/directory
#
# install:
#     - pip install -U platformio
#
# script:
#     - platformio ci --lib="." --board=ID_1 --board=ID_2 --board=ID_N
""")


def init_cvs_ignore(project_dir):
    ignore_path = join(project_dir, ".gitignore")
    default = [".pioenvs\n", ".piolibdeps\n"]
    current = []
    if isfile(ignore_path):
        with open(ignore_path) as fp:
            current = fp.readlines()
        if current and not current[-1].endswith("\n"):
            current[-1] += "\n"
    for d in default:
        if d not in current:
            current.append(d)
    with open(ignore_path, "w") as fp:
        fp.writelines(current)


def fill_project_envs(ctx, project_dir, board_ids, project_option, env_prefix,
                      force_download):
    content = []
    used_boards = []
    used_platforms = []

    config = util.load_project_config(project_dir)
    for section in config.sections():
        cond = [
            section.startswith("env:"), config.has_option(section, "board")
        ]
        if all(cond):
            used_boards.append(config.get(section, "board"))

    pm = PlatformManager()
    for id_ in board_ids:
        board_config = pm.board_config(id_)
        used_platforms.append(board_config['platform'])
        if id_ in used_boards:
            continue
        used_boards.append(id_)

        envopts = {"platform": board_config['platform'], "board": id_}
        # find default framework for board
        frameworks = board_config.get("frameworks")
        if frameworks:
            envopts['framework'] = frameworks[0]

        for item in project_option:
            if "=" not in item:
                continue
            _name, _value = item.split("=", 1)
            envopts[_name.strip()] = _value.strip()

        content.append("")
        content.append("[env:%s%s]" % (env_prefix, id_))
        for name, value in envopts.items():
            content.append("%s = %s" % (name, value))

    if force_download and used_platforms:
        _install_dependent_platforms(ctx, used_platforms)

    if not content:
        return

    with open(join(project_dir, "platformio.ini"), "a") as f:
        content.append("")
        f.write("\n".join(content))


def _install_dependent_platforms(ctx, platforms):
    installed_platforms = [
        p['name'] for p in PlatformManager().get_installed()
    ]
    if set(platforms) <= set(installed_platforms):
        return
    ctx.invoke(
        cli_platform_install,
        platforms=list(set(platforms) - set(installed_platforms)))
