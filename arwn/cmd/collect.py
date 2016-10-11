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
import daemon
import logging
import sys

import yaml

from arwn import engine


def parse_args():
    parser = argparse.ArgumentParser('arwn')
    parser.add_argument('-f', '--foreground',
                        help="run in foreground (don't daemonize)",
                        action='store_true', default=False)
    parser.add_argument('-c', '--config',
                        help="config file name",
                        default='config.yml')
    return parser.parse_args()


def setup_logger(logfile=None):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: "
                                  "%(message)s")
    if logfile is not None:
        fh = logging.FileHandler(logfile)
    else:
        fh = logging.StreamHandler(sys.stdout)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return fh, logger


def event_loop(config):
    dispatcher = engine.Dispatcher(
        config['device'],
        config['names'],
        config['mqtt']['server'],
        config
    )
    dispatcher.loopforever()


def main():
    args = parse_args()
    config = yaml.load(open(args.config, 'r').read())
    if not args.foreground:
        fh, logger = setup_logger(config['logfile'])
        try:
            with daemon.DaemonContext(files_preserve=[fh.stream, sys.stdout]):
                logger.debug("Starting arwn in daemon mode")
                event_loop(config)
        except Exception:
            logger.exception("Something went wrong!")
    else:
        fh, logger = setup_logger()
        logger.debug("Starting arwn in foreground")
        event_loop(config)
