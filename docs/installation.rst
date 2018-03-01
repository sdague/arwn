.. highlight:: shell

============
Installation
============

ARWN can use either an rfxcom receiver or an rtl-sdr dongle to acquire 433 Mhz
signals. The rfxcom receiver is more expensive and constrained on what sensors
it supports, though it does have better error correction built in. rtl-sdr
receivers can be purchased for ~$25 US on Amazon, so is the assumed default
installation.

Using an RTL-SDR
================

Install Linux on some system. A raspberry pi 3 is sufficient for the signal
processing required.

Install the rtl_433 project::

  git clone ..................
  cd rtl_433
  ./autogen
  ./configure
  make
  make install

Install the arwn project::

  pip install arwn

Configuration
=============

The config file is in yaml to make it easy to have nested structures, and
comments in the config file. There are 3 major sections.

* `collector` - configuration for which device will be used to listen to
  signals
* `wunderground` - wunderground credentials for reporting data up to weather
  underground from your sensors
* `names` - a pairing of device ids and names used for temperature sensors.

Collector
---------

The collector section defines how to listen to 433 Mhz signals.

* `type` - one of `rtl433` or `rfxcom`. Must be set.
*

inst

At the command line::

    $ easy_install arwn

Or, if you have virtualenvwrapper installed::

    $ mkvirtualenv arwn
    $ pip install arwn
