#!/usr/bin/env python2.7
#
#   ROTCTLD Basic Web GUI
#
#   Copyright (C) 2018  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
import json
import flask
from flask_socketio import SocketIO
import time
import socket
import sys
import datetime



# Define Flask Application, and allow automatic reloading of templates for dev
app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# SocketIO instance
socketio = SocketIO(app)

# Global setpoint and position variables
current_position = {'azimuth': 0.0, 'elevation': 0.0}
current_setpoint = {'azimuth': 0.0, 'elevation': 0.0}

# Home position azimuth , elevation
HOME_POS = [0.0, 0.0]


class ROTCTLD(object):
    """ rotctld (hamlib) communication class """
    # Note: This is a massive hack. 

    def __init__(self, hostname, port=4533, poll_rate=5, timeout=5, az_180 = False):
        """ Open a connection to rotctld, and test it for validity """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)

        self.hostname = hostname
        self.port = port


    def connect(self):
        """ Connect to rotctld instance """
        self.sock.connect((self.hostname,self.port))
        model = self.get_model()
        if model == None:
            # Timeout!
            self.close()
            raise Exception("Timeout!")
        else:
            return model


    def close(self):
        self.sock.close()


    def send_command(self, command):
        """ Send a command to the connected rotctld instance,
            and return the return value.
        """
        self.sock.sendall(command+'\n')
        try:
            return self.sock.recv(1024)
        except:
            return None


    def get_model(self):
        """ Get the rotator model from rotctld """
        model = self.send_command('_')
        return model


    def set_azel(self,azimuth,elevation):
        """ Command rotator to a particular azimuth/elevation """
        # Sanity check inputs.
        if elevation > 90.0:
            elevation = 90.0
        elif elevation < 0.0:
            elevation = 0.0

        if azimuth > 360.0:
            azimuth = azimuth % 360.0


        command = "P %3.1f %2.1f" % (azimuth,elevation)
        response = self.send_command(command)
        if "RPRT 0" in response:
            return True
        else:
            return False


    def get_azel(self):
        """ Poll rotctld for azimuth and elevation """
        # Send poll command and read in response.
        response = self.send_command('p')

        # Attempt to split response by \n (az and el are on separate lines)
        try:
            response_split = response.split('\n')
            _current_azimuth = float(response_split[0])
            _current_elevation = float(response_split[1])
            return (_current_azimuth, _current_elevation)
        except:
            logging.error("Could not parse position: %s" % response)
            return (None,None)


    def halt(self):
    	self.send_command('S')


# Rotator singleton object.
rotator = None

#
#   Flask Routes
#

@app.route("/")
def flask_index():
    """ Render main index page """
    return flask.render_template('index.html')


def flask_emit_event(event_name="none", data={}):
    """ Emit a socketio event to any clients. """
    socketio.emit(event_name, data, namespace='/update_status') 


# SocketIO Handlers

@socketio.on('client_connected', namespace='/update_status')
def update_client_display(data):
	flask_emit_event('position_event', current_position)
	flask_emit_event('setpoint_event', current_setpoint)


@socketio.on('update_setpoint', namespace='/update_status')
def update_azimuth_setpoint(data):
	_var = data['motor']
	_delta = data['delta']
	if _var == 'azimuth':
		print("Azimuth Setpoint:" + str(_delta))
		current_setpoint['azimuth'] = (current_setpoint['azimuth'] + _delta)%360.0
	elif _var == 'elevation':
		print("Elevation Setpoint:" + str(_delta))
		if (current_setpoint['elevation'] + _delta) > 90.0:
			current_setpoint['elevation'] = 90.0
		elif (current_setpoint['elevation'] + _delta) < 0.0:
			current_setpoint['elevation'] = 0.0
		else:
			current_setpoint['elevation'] += _delta
	else:
		print("Unknown!")

	rotator.set_azel(current_setpoint['azimuth'], current_setpoint['elevation'])
	update_client_display({})


@socketio.on('home_rotator', namespace='/update_status')
def home_rotator(data):
	current_setpoint['azimuth'] = HOME_POS[0]
	current_setpoint['elevation'] = HOME_POS[1]
	rotator.set_azel(current_setpoint['azimuth'], current_setpoint['elevation'])
	update_client_display({})


@socketio.on('halt_rotator', namespace='/update_status')
def halt_rotator(data):
	rotator.halt()



@socketio.on('get_position', namespace='/update_status')
def read_position(data):
	(_az, _el) = rotator.get_azel()

	if (_az == None):
		return
	else:
		current_position['azimuth'] = _az
		current_position['elevation'] = _el
		update_client_display({})



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--listen_port",default=5001,help="Port to run Web Server on. (Default: 5001)")
    parser.add_argument('--host', type=str, default='localhost', help="Rotctld server host. (Default: localhost)")
    parser.add_argument('--port', type=int, default=4533, help="Rotctld server port. (Default: 4533")
    args = parser.parse_args()

    # Try and connect to the rotator.
    try:
    	rotator = ROTCTLD(hostname=args.host, port=args.port)
    	_rot_model = rotator.connect()
    	print("Connected to rotctld - Rotator Model: " + str(_rot_model))

    except Exception as e:
    	print("Could not connect to rotctld server- %s" % str(e))
    	sys.exit(1)



    # Run the Flask app, which will block until CTRL-C'd.
    socketio.run(app, host='0.0.0.0', port=args.listen_port)

    rotator.close()

