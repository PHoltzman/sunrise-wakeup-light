import sys
import logging
import logging.handlers
import json
from datetime import datetime
import multiprocessing
import signal
from time import sleep


from dateutil import parser
from flask import Flask, request
from flask_restful import Api, Resource, reqparse, inputs
from werkzeug.exceptions import BadRequest

from timer import Timer
from programs import BaseProgram

########################### CONFIGURATION ###############################
NUM_PIXELS = 69
TIMER_FILE_NAME = 'timers.json'

########################### MODULE SETUP ###############################
# Setup logging handlers
formatter = logging.Formatter('%(asctime)s %(levelname)s %(process)d [%(thread)d] %(funcName)s: %(message)s')

ch1 = logging.StreamHandler()
ch1.setLevel(logging.DEBUG)
ch1.setFormatter(formatter)

ch2 = logging.handlers.TimedRotatingFileHandler('../logs/sunrise.log', when='midnight', backupCount=7)
ch2.setLevel(logging.DEBUG)
ch2.setFormatter(formatter)

CONTENT_TYPE_LIST = ['application/json', 'application/json;charset=utf-8', 'application/json; charset=utf-8', 'application/json;charset=UTF-8', 'application/json; charset=UTF-8']


########################### Application Setup ###############################
# Create the application and api
app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)
app.logger.addHandler(ch1)
app.logger.addHandler(ch2)

app.logger.info('Starting application')
api = Api(app, catch_all_404s=True)

STOP = multiprocessing.Event()

# Create program subprocess and start it running blackout program
PROGRAM_PROCESS = BaseProgram(app.logger, STOP, NUM_PIXELS)
PROGRAM_PROCESS.start()
PROGRAM_PROCESS.blackout()

	
def signal_handler(signal, frame):
	app.logger.info('SIGINT received. Cleaning up children processes and exiting...')
	STOP.set()
	sleep(2)
	PROGRAM_PROCESS.exit_gracefully()
	try:
		PROGRAM_PROCESS.join(5)
	except AttributeError:
		pass
	
	sys.exit(0)
		
signal.signal(signal.SIGINT, signal_handler)


#################### TIME ENDPOINTS #########################
@api.resource('/time')
class TimeAPI(Resource):
	'''API for managing time.'''
	
	def get(self):
		'''
		Fetch the time from the Raspberry Pi.
		
		Returns:
			JSON dict for Flask to send as response to client
		'''
		try:
			app.logger.info('Handling GET request on /time endpoint')
			resp = self.get_system_time()
			app.logger.info(resp)
			return resp, 200
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500
	
	def get_system_time(self):
		current_time = datetime.now()
		return {
			"currentTime": datetime_to_string(current_time)
		}
		

#################### TIMER ENDPOINTS #########################
@api.resource('/timers')
class TimersAPI(Resource):
	'''API for managing timers.'''
	
	def get(self):
		'''
		Query for all of the existing timers.
		
		Returns:
			JSON dict for Flask to send as response to client
		'''
		try:
			app.logger.info('Handling GET request on /timers endpoint')
			timer_dict = self.read_timers_from_file()
			
			for timer_id in timer_dict.iterkeys():
				timer_dict[timer_id] = timer_dict[timer_id].to_json()
			
			resp_dict = {"timers": timer_dict}
			app.logger.info(resp_dict)
			
			return resp_dict, 200
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500
	
	
	def post(self):
		'''
		Create a new timer.
		
		Returns:
			JSON dict for Flask to send as response to client
		'''
		try:
			app.logger.info('Handling POST request on /timers endpoint')

			# set up request parser to get easy validation for SOME arguments
			parser = reqparse.RequestParser(bundle_errors=True, trim=True)
			
			parser.add_argument('Content-Type', choices=CONTENT_TYPE_LIST, location='headers', required=True)
			parser.add_argument('triggerHour', type=int, location='json', required=True)
			parser.add_argument('triggerMinute', type=int, location='json', required=True)
			parser.add_argument('programToLaunch', location='json', required=True)
			
			request_dict = parser.parse_args()
			
			app.logger.info(request.json)
			
			try:
				arguments = request.json['arguments']
			except KeyError:
				arguments = None
			
			try:
				timer = Timer(request.json['triggerHour'], request.json['triggerMinute'], request.json['timerSchedule'], request.json['programToLaunch'], arguments)
			except InvalidTimerException as e:
				return {"error": e.message}, 400
			except KeyError as e:
				return {"error": e.message}, 400
			
			app.logger.info(timer.to_storage_json())
			timer_dict = self.read_timers_from_file()
			timer_dict[timer.timer_id] = timer
			timer.save_to_cron()
			self.write_timers_to_file(timer_dict)
			
			resp = timer.to_json()
			
			app.logger.info(resp)
			return resp, 200
		
		except BadRequest:
			app.logger.info('Bad request caught by Flask')
			raise
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500
	
	@staticmethod
	def read_timers_from_file():
		'''
		Read timers from the timer file into a dictionary
		
		Returns:
			timer_dict (dict) - dictionary of timers
		'''
		with open(TIMER_FILE_NAME, 'r') as f:
			timer_dict = json.loads(f.read())
			
		for timer_id in timer_dict.iterkeys():
			timer_dict[timer_id] = Timer.from_json(timer_dict[timer_id])
		
		return timer_dict
		
	
	@staticmethod
	def write_timers_to_file(timer_dict):
		'''
		Write all timers to the timer file.
		
		Arguments:
			timer_dict (dict) - dictionary of timers
		'''
		for timer_id in timer_dict.iterkeys():
			timer_dict[timer_id] = timer_dict[timer_id].to_storage_json()
				
		with open(TIMER_FILE_NAME, 'w') as f:
			f.write(json.dumps(timer_dict, indent=4))


	@staticmethod
	def get_timer_by_id(timer_id):
		'''
		Get a specific timer from the timer file based on timer_id.
		
		Arguments:
			timer_id (string) - id of the desired timer
			
		Raises:
			TimerNotFound
			
		Returns:
			Timer object for the desired timer
		'''
		timer_dict = TimersAPI.read_timers_from_file()
		
		try:
			return timer_dict[timer_id]
		
		except KeyError:
			raise TimerNotFound()
		

			
@api.resource('/timers/<timer_id>')
class TimerAPI(Resource):

	def get(self, timer_id):
		'''Get a specific timer'''
		app.logger.info('Handling GET request on /timers/{} endpoint'.format(timer_id))
		
		try:
			timer = TimersAPI.get_timer_by_id(timer_id)
			return timer.to_json(), 200
			
		except TimerNotFound:
			return {"error": "No timer found matching given id: {}".format(timer_id)}, 404
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500

				
	def put(self, timer_id):
		'''Modify a timer'''
		try:
			app.logger.info('Handling PUT request on /timers/{} endpoint'.format(timer_id))
			
			# set up request parser to get easy validation for SOME arguments
			parser = reqparse.RequestParser(bundle_errors=True, trim=True)
			
			parser.add_argument('Content-Type', choices=CONTENT_TYPE_LIST, location='headers', required=True)
			parser.add_argument('triggerHour', type=int, location='json', required=True)
			parser.add_argument('triggerMinute', type=int, location='json', required=True)
			parser.add_argument('programToLaunch', location='json', required=True)
			
			request_dict = parser.parse_args()
			
			app.logger.info(request.json)

			try:
				timer = TimersAPI.get_timer_by_id(timer_id)
				
				try:
					arguments = request.json['arguments']
				except KeyError:
					arguments = None
				
				try:
					timer = Timer(request.json['triggerHour'], request.json['triggerMinute'], request.json['timerSchedule'], request.json['programToLaunch'], arguments, timer_id)
				except InvalidTimerException as e:
					return {"error": e.message}, 400
				except KeyError as e:
					return {"error": e.message}, 400
				
				timer_dict = TimersAPI.read_timers_from_file()
				timer_dict[timer_id] = timer
				timer.save_to_cron()
				TimersAPI.write_timers_to_file(timer_dict)
				
				return timer.to_json(), 200
				
			except TimerNotFound:
				return {"error": "No timer found matching given id: {}".format(timer_id)}, 404
		
		
		except BadRequest:
			app.logger.info('Bad request caught by Flask')
			raise
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500
	
	
	
	def delete(self, timer_id):
		'''Delete a timer'''
		app.logger.info('Handling DELETE request on /timers/{} endpoint'.format(timer_id))
		
		try:
			timer = TimersAPI.get_timer_by_id(timer_id)
			
			timer_dict = TimersAPI.read_timers_from_file()
			timer_dict.pop(timer_id)
			timer.delete_from_cron()
			TimersAPI.write_timers_to_file(timer_dict)
			
			return {}, 204
			
		
		except TimerNotFound:
			return {"error": "No timer found matching given id: {}".format(timer_id)}, 404
		
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500



#################### PROGRAM ENDPOINTS #########################
@api.resource('/stop-program')
class StopProgramController(Resource):
	def get(self):
		'''End the currently executing program and go back to blackout'''
		try:
			global PROGRAM_PROCESS
			app.logger.info('Handling GET request on /stop-program endpoint')
			try:
				if PROGRAM_PROCESS.is_alive():
					current = PROGRAM_PROCESS.current_program
					STOP.set()
					PROGRAM_PROCESS.join()
					PROGRAM_PROCESS = None
					response = { "message": "stopped {} program successfully".format(current) }
				else:
					raise AttributeError
			except AttributeError:
				response = { "message": "no currently running program to stop" }
			
			return response, 200
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500

@api.resource('/programs')
class ProgramsAPI(Resource):	
	def get(self):
		'''Get currently executing program'''
		try:
			app.logger.info('Handling GET request on /programs endpoint')
			try:
				current_program = PROGRAM_PROCESS.current_program
			except Exception:
				current_program = None
			return { "currentProgram": current_program }, 200
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500
			

@api.resource('/programs/<program>')
class ProgramAPI(Resource):
	valid_programs = ["wakeup", "wakeup_demo", "single_color", "changing_color", "blackout"]
	
	def get(self, program):
		'''Run a program'''
		try:
			app.logger.info('Handling GET request on /programs/{} endpoint'.format(program))
			if program not in ProgramAPI.valid_programs:
				return {"error": "{} is not a recognized program".format(program)}, 404
				
			global PROGRAM_PROCESS
			
			# get the dict of url arguments in case they are needed
			query_dict = request.args.to_dict()
			
			# send the STOP command to existing program
			try:
				if PROGRAM_PROCESS.is_alive():
					STOP.set()
			except AttributeError:
				pass
			
			
			if program == 'single_color':
				if 'red' in query_dict:
					red = int(query_dict['red'])
				else:
					red = 0
					
				if 'green' in query_dict:
					green = int(query_dict['green'])
				else:
					green = 0
					
				if 'blue' in query_dict:
					blue = int(query_dict['blue'])
				else:
					blue = 0
					
				try:					
					if red < 0 or red > 255 or green < 0 or green > 255 or blue < 0 or blue > 255:
						raise ValueError
						
				except (KeyError, ValueError, TypeError):
					return { "error": "red, green, and blue values must be integers between 0 and 255." }, 400
					
				PROGRAM_PROCESS.single_color(red, green, blue)
				
			elif program == 'changing_color':
				PROGRAM_PROCESS.changing_color()
					
					
			elif program == 'blackout':
				PROGRAM_PROCESS.blackout()
				
				
			elif program == 'wakeup':
				multiplier = None
				try:
					multiplier = int(query_dict['multiplier'])
					
					if multiplier < 0:
						raise ValueError
				
				except KeyError:
					pass
				
				except (ValueError, TypeError):
					return { "error": "if provided, 'multiplier' must be an integer greater than 0" }, 400
				
				PROGRAM_PROCESS.wakeup(multiplier)
			
			
			elif program == 'wakeup_demo':
				PROGRAM_PROCESS.wakeup(1)
				
			return {}, 200
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500

			

	
	
	
#################### STANDARD ENDPOINTS ###########################	
@api.resource('/')
class ServiceInfoAPI(Resource):
	'''API for the root (service info) endpoint.'''
	
	def get(self):
		'''
		GET verb for the endpoint.
		
		Returns:
		JSON dict for Flask to send as response to client
		'''
		try:
			app.logger.info('Handling request on / endpoint')
			return self.create_service_info_response(), 200
		except Exception:
			return { "error": "Error retrieving environment variables for populating service info." }, 500
		
		
	def create_service_info_response(self):
		resp = {
			"name": "sunrise",
			"apiVersion": "1.0",
		}
		
		return resp
		

#################### CUSTOM EXCEPTIONS ###########################	
class TimerNotFound(Exception):
	pass

class InvalidTimerException(Exception):
	pass

	
######################## MISC FUNCTIONS ###########################	
def datetime_to_string(d_time):
	"""
	Convert datetime object to ISO8601 compliant string representation.
	output format = "%Y-%m-%dT%H:%M:%S.%fZ"
	
	Keyword arguments:
	d_time -- timezone agnostic datetime object in UTC
	
	Returns:
	s_time -- formatted string of the datetime
	"""
	output_datetime_format = "%Y-%m-%dT%H:%M:%S"
	s_time = datetime.strftime(d_time, output_datetime_format)
	
	return s_time	
	
	
########################## INVOCATION #############################	
if __name__ == "__main__":
	app.run(host='0.0.0.0', port=8081)