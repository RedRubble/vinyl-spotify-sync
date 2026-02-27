# 🎶 Vinyl-Spotify-Sync

**Vinyl-Spotify-Sync** is a Python application for the Raspberry Pi that listens for background music, identifies the
song, and plays the song on a specified device.

This project is a fork of [Now-Playing](https://spotipy.readthedocs.io/en/2.25.1/), with the change to play music
to a Spotify device, rather than display to an eink display.

> This project was born out of a personal need: I love listening to vinyl, but since it's analog, I wasn't able to
> easily tell what song was playing. Sure, you can count the spaces in the grooves, but that's not exactly convenient.
> The same goes for music in films—I'd often reach for my phone to Shazam a song. Now, I just glance at my display.

## 🚀 Features

- Detects music using a
  local [YAMNet](https://www.kaggle.com/models/google/yamnet/tensorFlow2/yamnet/1?tfhub-redirect=true) ML model
- When music is detected, identifies the song with [ShazamIO](https://github.com/shazamio/ShazamIO)
- Begins playing the song on a specified Spotify device with [Spotipy](https://spotipy.readthedocs.io/en/2.25.1/)

## ✨ What's New?

This project builds on and refactors several previous works (see [LICENSE](./LICENSE)).

- [Now-Playing](https://spotipy.readthedocs.io/en/2.25.1/)
- [spotipi-eink (original)](https://github.com/ryanwa18/spotipi-eink)
- [spotipi-eink (fork)](https://github.com/Gabbajoe/spotipi-eink)
- [shazampi-eink (fork)](https://github.com/ravi72munde/shazampi-eink)

## 📦 Installation & Setup

### 🔧 Required Hardware

- [Raspberry Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) *(or newer)*
- [MicroSD card](https://www.raspberrypi.com/products/sd-cards/)
- [Power supply](https://www.raspberrypi.com/products/micro-usb-power-supply/)
- [USB microphone](https://www.amazon.com.be/microphone-portable-enregistrement-vid%C3%A9oconf%C3%A9rences-n%C3%A9cessaire/dp/B09PVPPRF2?source=ps-sl-shoppingads-lpcontext&ref_=fplfs&ref_=fplfs&psc=1&smid=A3HYZLWFA5CWB0&gQT=1)
  *(min. 16kHz sample rate)*
- [USB-A to Micro-USB adapter](https://www.amazon.com.be/-/nl/Magnet-Adapter-Compatibel-Smartphones-randapparatuur/dp/B0CCSK6TWR/ref=sr_1_4?dib=eyJ2IjoiMSJ9.tSkQ7Eow3VuzOmbOparC3w6W72C_2lR7qR6GDXXFon_pZWGesfG0THfUPlsK47bxatu_2L-ennJAbfJOnxkvAT4PFFmsaLdhD5TxbF6-b5x0BBZ0cBfAzrGtuyrV64W2uwanSiruEmp4YzTr0veXeH0LK_YwEbmg6Cle6MP-_0hbOrEqdH83qKTqznjk0VJGjp1CmIb6v7-nMhO1tOFbc92DTz2RPYz207CHCzUXVuhVMyWsGMFb8oPqwCK_YbKaQtH0P0bKZqHN-uCreQRhWDefUiY6TUM6f6ryPNx2IaI.jD_UeNFvfX1JIecvwtP37jqDSlPx_A_PXUSiTBfzqCU&dib_tag=se&keywords=usb+a+to+micro+usb&qid=1752774830&s=electronics&sr=1-4)
  *(if your microphone is of type USB-A)*
- Optional: [3D printed case](https://github.com/scripsi/inky-impression-case)

### 🥧 Raspberry Pi OS

1. Flash Raspberry Pi OS Lite to your microSD card
   using [Raspberry Pi Imager](https://www.raspberrypi.com/documentation/computers/getting-started.html#installing-the-operating-system)
2. In the setup wizard, enable:
    - Wi-Fi
    - SSH — to allow remote access, as the OS is headless

### 🔐 Required Credentials

#### 🎵 Spotify API

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click 'Create App' and fill out the form:
    1. App name
    2. App description
    3. Redirect URI = http://127.0.0.1:8888/callback
    4. Check 'Web API'
    5. Check the 'Terms of Service'
3. Click on 'Save'
4. Store your Client ID and Client Secret, you will need it later

#### 🎟 Spotify Access Token

Since Raspberry Pi OS Lite is headless (no browser), you must authorize Spotify once from a computer:

1. On your computer, clone this repo:

```bash 
  git clone https://github.com/maurocastermans/now-playing
  cd now-playing
```

2. Fill in your `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in `spotify_auth_helper.py`
3. Run the script:

```bash
  python3 spotify_auth_helper.py
```

4. Follow the browser prompt and allow access to your Spotify account. This will generate a .cache file locally
   containing your Spotify access token.

### ⚙️ Installation Script

SSH into your Raspberry Pi:

```bash
  ssh <username>@<ip-address>
```

And run:

```bash
  wget https://raw.githubusercontent.com/maurocastermans/now-playing/main/setup.sh
  chmod +x setup.sh
  bash ./setup.sh
```

Afterwards, copy the .cache file from your local computer to the now-playing project root. Spotipy will from now on
automatically refresh the
access token when it expires (using the refresh token present in the .cache file)

The `setup.sh` script will automatically start the now-playing systemd service. Verify that the service starts without
errors:

```bash
  journalctl -u now-playing.service --follow
```

Should you encounter any errors, check [Known Issues](#-known-issues)

> 🧙 <b>What the Script Does</b>
>
> - Enables SPI and I2C
> - Updates the system and installs dependencies
> - Sets up a Python virtual environment and installs Python packages
> - Creates config, log, and resources directories
> - Prompts for credentials, your device name and generates config.yaml
> - Copies and configures a systemd service to autostart on boot
> - Starts the now-playing service

> 📂 <b>Resulting Config</b>
>
> ```yaml
> spotify:
>   client_id: "YOUR_SPOTIFY_CLIENT_ID"
>   client_secret: "YOUR_SPOTIFY_CLIENT_SECRET"
>   playlist_id: "YOUR_SPOTIFY_PLAYLIST_ID"
>   device_name: "YOUR_DEVICE_NAME"
> 
> log:
>   log_file_path: "log/now_playing.log"
> ```

## 🛠 Useful Commands

### 📝 Edit Configuration

To update your configuration after installation:

```bash
  nano config/config.yaml
```

After editing, restart the service to apply changes:

```bash
  sudo systemctl restart now-playing.service
```

### 🔁 Systemd Service

- Check status:

```bash
  sudo systemctl status now-playing.service
```

- Start/Stop:

```bash
  sudo systemctl stop now-playing.service
  sudo systemctl start now-playing.service
```

- Logs:

```bash
  journalctl -u now-playing.service
  journalctl -u now-playing.service --follow
  journalctl -u now-playing.service --since today
  journalctl -u now-playing.service -b
```

### 🧪 Manual Python Execution

Now-playing runs in a Python virtual environment (using venv). If you want to run the Python code manually:

```bash
  sudo systemctl stop now-playing.service
  source venv/bin/activate
  python3 src/now_playing.py
```

To leave the virtual environment:

```bash
  deactivate
```

## 🐛 Known Issues

### Low USB Microphone Gain

Some USB microphones have very low default input gain, meaning they only pick up sound when your audio device is
extremely close to the mic. This can cause issues with audio detection.

To boost your microphone’s gain:

1. Open the audio mixer:

```bash
    alsamixer
```

2. Select your USB microphone:
    1. Press F6 to open the sound card list
    2. Use the arrow keys to select your USB microphone device
3. Adjust the input gain:
    1. Press F4 to switch to Capture controls
    2. Increase the gain using the ↑ arrow key until it reaches an appropriate level
4. Save the gain settings (so they persist after reboot):

```bash
  sudo alsactl store
