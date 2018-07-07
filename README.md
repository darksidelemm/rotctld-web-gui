# Basic Rotctld Web GUI
Mark Jessop 2018-07-07

This repository contains a very basic rotctld control web interface, targeted for use on a mobile browser.
I wrote this out of a need to have an easy way to test a new az/el rotator while on a roof, with the controller down in my radio shack.

It is in no way polished, and likely has some interesting bugs (particulatly if multiple clients are connected). Take caution when using it to control expensive antenna arrays!!!


## Dependencies
* Python (2.7, until I fix things)
* Python Modules: flask, flask-socketio  (can obtain using pip)

## Usage:
* Start rotctld (refer rotctld documentation)
* `python rotatorgui.py`
* Navigate to http://localhost:5001/   (or equivalent IP)

Run `python rotatorgui.py --help` for command line options:
