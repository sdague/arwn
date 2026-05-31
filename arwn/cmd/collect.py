#!/usr/bin/env python
#
# Copyright 2016 Sean Dague
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import logging
import os
import sys

import colorlog
import yaml

from arwn import engine
from arwn.config import Config


def parse_args():
    parser = argparse.ArgumentParser("arwn")
    parser.add_argument("-c", "--config", help="config file name", default="config.yml")
    return parser.parse_args()


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s[%(levelname)s]%(reset)s %(name)s: %(message)s"
    )
    fh = logging.StreamHandler(sys.stdout)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def event_loop(config, config_path):
    dispatcher = engine.Dispatcher(config)
    watcher = engine.ConfigWatcher(config_path, dispatcher)
    try:
        watcher.start()
        dispatcher.loopforever()
    finally:
        watcher.stop()


def main():
    args = parse_args()
    with open(args.config, "r") as f:
        config = Config.from_dict(yaml.safe_load(f))
    config_path = os.path.abspath(args.config)
    logger = setup_logger()
    logger.debug("Starting arwn")
    event_loop(config, config_path)
