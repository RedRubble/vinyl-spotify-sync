#!/bin/bash

if [[ $EUID -eq 0 ]]; then
  echo "Error: This script must NOT be run as root. Please run it as a regular user." >&2
  exit 1
fi

echo "==> Updating package lists..."
sudo apt update && echo "✔ Package lists updated successfully."

echo "==> Upgrading system packages to the latest versions..."
sudo apt upgrade -y && echo "✔ System packages upgraded successfully."

echo "==> Installing required system dependencies..."
sudo apt-get install python3-numpy git libopenjp2-7 libportaudio2 -y \
  && echo "✔ System dependencies installed successfully."

if [ -d "now-playing" ]; then
    echo "==> Found an existing installation of now-playing. Removing it..."
    sudo rm -rf now-playing && echo "✔ Old installation removed."
fi

echo "==> Cloning the now-playing project from GitHub..."
git clone https://github.com/RedRubble/vinyl-spotify-sync && echo "✔ Project cloned successfully."
echo "Switching to the installation directory."
cd now-playing || exit
install_path=$(pwd)

echo "==> Setting up a Python virtual environment..."
python3 -m venv --system-site-packages venv && echo "✔ Python virtual environment created."
echo "Activating the virtual environment..."
source "${install_path}/venv/bin/activate" && echo "✔ Virtual environment activated."

echo "==> Upgrading pip in the virtual environment..."
pip install --upgrade pip && echo "✔ Pip upgraded successfully."

echo "==> Installing required Python packages..."
pip3 install -r requirements.txt --upgrade && echo "✔ Python packages installed successfully."

echo "==> Setting up configuration, resources and log directories..."
if ! [ -d "${install_path}/config" ]; then
    echo "Creating config directory..."
    mkdir -p "${install_path}/config" && echo "✔ Config directory created."
fi
if ! [ -d "${install_path}/resources" ]; then
    echo "Creating resources directory..."
    mkdir -p "${install_path}/resources" && echo "✔ Resources directory created."
fi
if ! [ -d "${install_path}/log" ]; then
    echo "Creating log directory..."
    mkdir -p "${install_path}/log" && echo "✔ Log directory created."
fi

echo "==> Setting up the Spotify API..."
echo "Please enter your Spotify client ID:"
read -r spotify_client_id
echo "Please enter your Spotify client secret:"
read -r spotify_client_secret
echo "Please enter your Spotify device name:"
read -r spotify_device_name

cat <<EOF > "${install_path}/config/config.yaml"
spotify:
  client_id: "${spotify_client_id}"
  client_secret: "${spotify_client_secret}"
  device_name: "${device_name}"

log:
  log_file_path: "${install_path}/log/now_playing.log"

EOF
echo "✔ Configuration file created at ${install_path}/config/config.yaml."

echo "==> Setting up the now-playing systemd service..."
if [ -f "/etc/systemd/system/now-playing.service" ]; then
    echo "Removing old now-playing systemd service..."
    sudo systemctl stop now-playing
    sudo systemctl disable now-playing
    sudo rm -rf /etc/systemd/system/now-playing.*
    sudo systemctl daemon-reload
    echo "✔ Old now-playing systemd service removed."
fi
sudo cp "${install_path}/now-playing.service" /etc/systemd/system/
sudo sed -i -e "/\[Service\]/a ExecStart=${install_path}/venv/bin/python3 ${install_path}/src/now_playing.py" /etc/systemd/system/now-playing.service
sudo sed -i -e "/ExecStart/a WorkingDirectory=${install_path}" /etc/systemd/system/now-playing.service
sudo sed -i -e "/RestartSec/a User=$(id -u)" /etc/systemd/system/now-playing.service
sudo sed -i -e "/User/a Group=$(id -g)" /etc/systemd/system/now-playing.service

sudo systemctl daemon-reload
sudo systemctl start now-playing
sudo systemctl enable now-playing
echo "✔ now-playing systemd service installed and started."

echo "🎉 Setup is complete!"
