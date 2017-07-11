#!/bin/bash

set -e

echo "Installer for systemd based systems"

if [[ ! -d .venv ]]; then
    virtualenv .venv
fi
source .venv/bin/activate

pip install -e .

DIR=$(pwd)
USER=$(whoami)

echo "Writing systemd unit file"

cat - > arwn.service <<EOF
[Unit]
Description = ARWN Collector

[Service]
WorkingDirectory = $DIR
ExecStart = $DIR/.venv/bin/arwn-collect -f
Type = simple
User = $USER
Group = dialout
Restart = always

[Install]
WantedBy = multi-user.target

EOF

echo "Installing systemd unit file and starting..."

sudo cp arwn.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable arwn
sudo systemctl start arwn
