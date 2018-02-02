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

from timer import Timer, Timers, TimerNotFound, InvalidTimerException
from programs import BaseProgram, ProgramTask, ProgramList


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

# queue for communicating with the subprocess
QUEUE = multiprocessing.JoinableQueue()

# Create program subprocess and start it running blackout program
PROGRAM_PROCESS = BaseProgram(app.logger, QUEUE, NUM_PIXELS)
PROGRAM_PROCESS.start()
QUEUE.put_nowait(ProgramTask('blackout'))
	
def signal_handler(signal, frame):
	app.logger.info('SIGINT received. Cleaning up children processes and exiting...')
	QUEUE.put_nowait(ProgramTask('KILL'))
	sleep(2)
	QUEUE.join(2)
	try:
		PROGRAM_PROCESS.join(2)
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
			timers_obj = Timers(app.logger, TIMER_FILE_NAME)
			timer_dict = timers_obj.read_timers_from_file()
			
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
		Create or modify a timer.
		
		Returns:
			JSON dict for Flask to send as response to client
		'''
		try:
			app.logger.info('Handling POST request on /timers endpoint')

			# set up request parser to get easy validation for SOME arguments
			parser = reqparse.RequestParser(bundle_errors=True, trim=True)
			
			parser.add_argument('Content-Type', choices=CONTENT_TYPE_LIST, location='headers', required=True)
			parser.add_argument('timerId', location='json', required=True)
			parser.add_argument('triggerHour', type=int, location='json', required=True)
			parser.add_argument('triggerMinute', type=int, location='json', required=True)
			parser.add_argument('programToLaunch', location='json', required=True)
			parser.add_argument('isEnabled', type=inputs.boolean, location='json', required=False)
			
			request_dict = parser.parse_args()
			
			app.logger.info(request.json)
			
			try:
				arguments = request.json['arguments']
			except KeyError:
				arguments = None
			
			try:
				timer = Timer(app.logger, request_dict['timerId'], request_dict['triggerHour'], request_dict['triggerMinute'], request.json['timerSchedule'], request_dict['programToLaunch'], request_dict['isEnabled'], arguments)
			except InvalidTimerException as e:
				return {"error": e.message}, 400
			except KeyError as e:
				return {"error": e.message}, 400
			
			timers_obj = Timers(app.logger, TIMER_FILE_NAME)
			timers_obj.add_or_modify_timer(timer)
			resp = timer.to_json()
			
			app.logger.info(resp)
			return resp, 200
		
		except BadRequest:
			app.logger.info('Bad request caught by Flask')
			raise
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500

			
@api.resource('/timers/<timer_id>')
class TimerAPI(Resource):

	def get(self, timer_id):
		'''Get a specific timer'''
		app.logger.info('Handling GET request on /timers/{} endpoint'.format(timer_id))
		
		try:
			timers_obj = Timers(app.logger, TIMER_FILE_NAME)
			timer = timers_obj.get_timer_by_id(timer_id)
			return timer.to_json(), 200
			
		except TimerNotFound:
			return {"error": "No timer found matching given id: {}".format(timer_id)}, 404
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500
	
	def delete(self, timer_id):
		'''Delete a timer'''
		app.logger.info('Handling DELETE request on /timers/{} endpoint'.format(timer_id))
		
		try:
			timers_obj = Timers(app.logger, TIMER_FILE_NAME)
			timers_obj.delete_timer(timer_id)		
			return {}, 204
			
		except TimerNotFound:
			return {"error": "No timer found matching given id: {}".format(timer_id)}, 404
		
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500

@api.resource('/timers/<timer_id>/enable')
class TimerEnableAPI(Resource):

	def get(self, timer_id):
		'''Enable a specific timer'''
		app.logger.info('Handling GET request on /timers/{}/enable endpoint'.format(timer_id))
		
		try:
			timers_obj = Timers(app.logger, TIMER_FILE_NAME)
			timer = timers_obj.enable_timer(timer_id)
			return timer.to_json(), 200
			
		except TimerNotFound:
			return {"error": "No timer found matching given id: {}".format(timer_id)}, 404
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500
			
@api.resource('/timers/<timer_id>/disable')
class TimerDisableAPI(Resource):

	def get(self, timer_id):
		'''Enable a specific timer'''
		app.logger.info('Handling GET request on /timers/{}/disable endpoint'.format(timer_id))
		
		try:
			timers_obj = Timers(app.logger, TIMER_FILE_NAME)
			timer = timers_obj.disable_timer(timer_id)
			return timer.to_json(), 200
			
		except TimerNotFound:
			return {"error": "No timer found matching given id: {}".format(timer_id)}, 404
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500

#################### PROGRAM ENDPOINTS #########################
@api.resource('/programs')
class ProgramsAPI(Resource):	
	def get(self):
		'''Get currently executing program'''
		try:
			app.logger.info('Handling GET request on /programs endpoint')
			try:
				app.logger.info(PROGRAM_PROCESS.current_program)
				current_program = PROGRAM_PROCESS.current_program
			except Exception as e:
				app.logger.error('Issue getting current program', exc_info=True)
				current_program = None
			return { "currentProgram": current_program }, 200
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500
			

@api.resource('/programs/<program>')
class ProgramAPI(Resource):
	
	def get(self, program):
		'''Run a program'''
		try:
			app.logger.info('Handling GET request on /programs/{} endpoint'.format(program))
			if program not in ProgramList.valid_programs:
				return {"error": "{} is not a recognized program".format(program)}, 404
				
			# get the dict of url arguments in case they are needed
			query_dict = request.args.to_dict()
			
			if program == 'blackout':
				QUEUE.put_nowait(ProgramTask('blackout'))
				
			elif program == 'single_color':
				try:
					if 'red' in query_dict:
						query_dict['red'] = int(query_dict['red'])
						if query_dict['red'] < 0 or query_dict['red'] > 255:
							raise ValueError
						
					if 'green' in query_dict:
						query_dict['green'] = int(query_dict['green'])
						if query_dict['green'] < 0 or query_dict['green'] > 255:
							raise ValueError
					
					if 'blue' in query_dict:
						query_dict['blue'] = int(query_dict['blue'])
						if query_dict['blue'] < 0 or query_dict['blue'] > 255:
							raise ValueError
						
				except (KeyError, ValueError, TypeError):
					return { "error": "red, green, and blue values must be integers between 0 and 255." }, 400
					
				QUEUE.put_nowait(ProgramTask('single_color', query_dict))
				
			elif program == 'changing_color':
				QUEUE.put_nowait(ProgramTask('changing_color'))
					
				
			elif program == 'wakeup':
				try:
					if 'multiplier' in query_dict:
						query_dict['multiplier'] = int(query_dict['multiplier'])
						if query_dict['multiplier'] < 0:
							raise ValueError
				
				except (ValueError, TypeError):
					return { "error": "if provided, 'multiplier' must be an integer greater than 0" }, 400
				
				QUEUE.put_nowait(ProgramTask('wakeup', query_dict))
			
			
			elif program == 'wakeup_demo':
				QUEUE.put_nowait(ProgramTask('wakeup', {'multiplier': 1}))
				
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