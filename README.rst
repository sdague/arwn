===============================
Ambient Radio Weather Network
===============================

.. image:: https://img.shields.io/pypi/v/arwn.svg
        :target: https://pypi.python.org/pypi/arwn

.. image:: https://img.shields.io/travis/sdague/arwn.svg
        :target: https://travis-ci.org/sdague/arwn

..
   .. image:: https://readthedocs.org/projects/arwn/badge/?version=latest
           :target: https://readthedocs.org/projects/arwn/?badge=latest
           :alt: Documentation Status


Collect 433Mhz weather sensor data and publish to mqtt.

This software is designed to use an rfxcom usb receiver or an rtl 433
compatible receiver, and relay the data found on it over an mqtt bus
so that it can be consumed by other software, such as Home Assistant.

Installation Requirements
=========================

You will need a Linux system (raspberry pi is sufficient) and a 433
MHz receiver. This supports either rfxcom receivers for rtl-sdr
dongles.

- Install hardware + support code

  - If using an rfxcom receiver, all supporting software is included.

  - If using an rtl-sdr dongle, you must also install the rtl433
    project from source.

- pip install arwn

Configuration
=============

Copy the config.yml.sample file and modify it accordingly.

Credits
---------

Sean Dague
