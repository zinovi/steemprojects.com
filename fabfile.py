# -*- coding: utf-8 -*-
"""
This is a collection of useful utility functions when working with docker on different environments.
In order to use these functions, install fabric on your local machine with::
    pip install fabric
Please note: Fabric is a remote code execution tool, NOT a remote configuration tool. While you can copy files
from here to there, it is not a good replacement for salt or ansible in this regard.
There is a function called `production` where you need to fill in the details about your production machine(s).
You can then run::
    fab production status
to get the status of your stack
To list all available commands, run::
    fab -l
"""


from fabric.operations import local as lrun, run, sudo, put
from fabric.api import *
from fabric.colors import green, red, yellow, blue
import os
import datetime
import tempfile
import time


def local():
    """
    Work on the local environment
    """
    env.compose_file = "dev.yml"
    env.project_dir = "."
    env.run = lrun
    env.cd = lcd


def production():
    """
    Work on the production environment
    """
    env.hosts = ["94.23.220.88"]  # list the ip addresses or domain names of your production boxes here
    env.port = 22  # ssh port
    env.user = "deploy"  # remote user, see `env.run` if you don't log in as root

    env.compose_file = "docker-compose.yml"
    env.project_dir = "/home/deploy/Deploy/steemprojects.com"  # this is the project dir where your code lives on this machine
    env.data_dir = "/home/deploy/Data/steemprojects.com"

    # if you don't use key authentication, add your password here
    # env.password = "foobar"
    # if your machine has no bash installed, fall back to sh
    # env.shell = "/bin/sh -c"

    env.run = run  # if you don't log in as root, replace with 'env.run = sudo'
    env.cd = cd


def copy_secrets():
    """
    Copies secrets from local to remote.
    :return:
    """
    secrets = [
        ".env",
    ]

    for secret in secrets:
        remote_path = "/".join([env.project_dir, secret])
        print(blue("Copying {secret} to {remote_path} on {host}".format(
            secret=secret, remote_path=remote_path, host=env.host
        )))
        put(secret, remote_path)

        DEPLOYMENT_DATETIME = datetime.datetime.utcnow().isoformat()
        with cd(env.project_dir):
            run("echo 'DEPLOYMENT_DATETIME=%s' >> %s" % (DEPLOYMENT_DATETIME, secret))


def rollback(commit="HEAD~1"):
    """
    Rollback to a previous commit and build the stack
    :param commit: Commit you want to roll back to. Default is the previous commit
    """
    with env.cd(env.project_dir):
        env.run("git checkout {}".format(commit))

    deploy()


def deploy():
    """
    Pulls the latest changes from master, rebuilt and restarts the stack
    """

    lrun("git push origin master")
    copy_secrets()
    with env.cd(env.project_dir):

        #docker_compose("run postgres backup")

        env.run("git pull origin master")

        build_and_restart("django-a")
        time.sleep(10)

        # just to make sure they are on
        docker_compose("start postgres")
        docker_compose("start redis")
        time.sleep(10)

        build_and_restart("django-b")


def build_and_restart(service):
    docker_compose("build " + service)
    docker_compose("create " + service)
    docker_compose("stop " + service)
    docker_compose("start " + service)


def docker_compose(command):
    """
    Run a docker-compose command
    :param command: Command you want to run
    """
    with env.cd(env.project_dir):
        return env.run("docker-compose -f {file} {command}".format(file=env.compose_file, command=command))


def download_db(filename="tmp.sql"):
    with env.cd(env.project_dir):
        docker_compose("run postgres backup {}".format(filename))
        remote_sql_dump_filepath = os.path.join(env.data_dir, 'backups', filename)

        get(remote_sql_dump_filepath, './backups/{}'.format(filename))

        docker_compose("run postgres rm /backups/{}".format(filename))
        print("Remote done!")

    local()

    with env.cd(env.project_dir):
        docker_compose("down -v")
        docker_compose("up -d postgres")
        time.sleep(10)
        docker_compose("run postgres restore {}".format(filename))
        docker_compose("run django python manage.py migrate")
        docker_compose("up -d")
        env.run("rm ./backups/{}".format(filename))
        print("Local done!")

    print(green("Your local environment has now new database!"))


def download_media():
    temp_dirpath = tempfile.mkdtemp()

    env.run("mkdir -p {}".format(temp_dirpath))
    with env.cd(temp_dirpath):
        container_id = docker_compose("ps -q django-a").split()[0]
        env.run(
            "docker cp {}:/data/media/ {}".format(
                container_id,
                temp_dirpath
            )
        )
        get("{}/media/".format(temp_dirpath), "./")

    env.run("rm -rf {}".format(temp_dirpath))
