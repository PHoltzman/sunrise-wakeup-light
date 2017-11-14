import sys
import logging
import logging.handlers

import json
from datetime import datetime
from uuid import uuid4
import multiprocessing
import signal
from time import sleep


from dateutil import parser
from flask import Flask, request
from flask_restful import Api, Resource, reqparse, inputs
from werkzeug.exceptions import BadRequest
from crontab import CronTab
import rpi_ws281x as rpi

NUM_PIXELS = 69


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

cron = CronTab(user='pi')
PROGRAM_PROCESS = None
QUIT = multiprocessing.Event()

	
def signal_handler(signal, frame):
	app.logger.info('SIGINT received. Cleaning up children processes and exiting...')
	QUIT.set()
	sleep(2)
	# try:
		# PROGRAM_PROCESS.join(5)
	# except AttributeError:
		# pass
	
	sys.exit(0)
		
signal.signal(signal.SIGINT, signal_handler)

#################### FUNCTIONAL ENDPOINTS #########################
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
		

@api.resource('/timers')
class TimersAPI(Resource):
	'''API for managing timers.'''
	
	timer_file = 'timers.json'
	
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
		with open(TimersAPI.timer_file, 'r') as f:
			timer_dict = json.loads(f.read())
			
		for timer_id in timer_dict.iterkeys():
			timer_dict[timer_id] = Timer.from_json(timer_dict[timer_id])
		
		return timer_dict
		
	
	@staticmethod
	def write_timers_to_file(timer_dict):
		for timer_id in timer_dict.iterkeys():
			timer_dict[timer_id] = timer_dict[timer_id].to_storage_json()
				
		with open(TimersAPI.timer_file, 'w') as f:
			f.write(json.dumps(timer_dict, indent=4))


	@staticmethod
	def get_timer_by_id(timer_id):
		timer_dict = TimersAPI.read_timers_from_file()
		
		try:
			return timer_dict[timer_id]
		
		except KeyError:
			raise TimerNotFound()
		

			
@api.resource('/timers/<timer_id>')
class TimerAPI(Resource):

	def get(self, timer_id):
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


class Timer(object):

	def __init__(self, trigger_hour, trigger_minute, timer_schedule, program_to_launch, arguments=None, timer_id=None):
		
		if timer_id is None:
			self.timer_id = str(uuid4())
		else:
			self.timer_id = timer_id
		
		try:
			if not (trigger_hour >= 0 and trigger_hour <=23):
				raise InvalidTimerException("Trigger hour must be between 0 and 23")
			
			if not (trigger_minute >= 0 and trigger_minute <= 59):
				raise InvalidTimerException("Trigger minute must be between 0 and 23")
				
			self.trigger_hour = trigger_hour
			self.trigger_minute = trigger_minute
		except Exception:
			raise InvalidTimerException("Could not parse input time")
			
		if program_to_launch in ProgramAPI.valid_programs:
			self.program_to_launch = program_to_launch
		else:
			raise InvalidTimerException("{} is not a valid program to launch.".format(program_to_launch))
		
		self.arguments = arguments
		if arguments is not None:
			if not isinstance(arguments, dict):
				raise InvalidTimerException("Arguments list must be key/value pairs")
		
		self.timer_schedule = self.ingest_timer_schedule(timer_schedule)


	def ingest_timer_schedule(self, timer_schedule):
		valid_entries = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
		
		for item in timer_schedule:
			if item not in valid_entries:
				raise InvalidTimerException('{} is not a valid entry for a timer schedule'.format(item))
		
		a = [self.dow_to_num(x) for x in timer_schedule]
		b = set(a)
		sched = list(b)
		
		return sched

	
	@staticmethod
	def dow_to_num(dow):
		d = dow.lower()
		if d == 'mon':
			return 1
		elif d == 'tue':
			return 2
		elif d == 'wed':
			return 3
		elif d == 'thu':
			return 4
		elif d == 'fri':
			return 5	
		elif d == 'sat':
			return 6
		elif d == 'sun':
			return 7
	
	@staticmethod
	def num_to_dow(num):
		if num == 1:
			return 'mon'
		elif num == 2:
			return 'tue'
		elif num == 3:
			return 'wed'
		elif num == 4:
			return 'thu'
		elif num == 5:
			return 'fri'
		elif num == 6:
			return 'sat'
		elif num == 7:
			return 'sun'
		
	@classmethod
	def from_json(cls, json_dict):
		timer_id = None
		if 'timerId' in json_dict:
			timer_id = json_dict['timerId']
		
		try:
			args = json_dict['arguments']
		except KeyError:
			args = None
			
		if json_dict['timerSchedule'] is not None:
			if isinstance(json_dict['timerSchedule'][0], int):
				json_dict['timerSchedule'] = [cls.num_to_dow(x) for x in json_dict['timerSchedule']]
			
		time_obj = Timer(json_dict['triggerHour'], json_dict['triggerMinute'], json_dict['timerSchedule'], json_dict['programToLaunch'], args, timer_id)
		return time_obj
	
	def to_storage_json(self):
		resp = {
			'timerId': self.timer_id,
			'triggerHour': self.trigger_hour,
			'triggerMinute': self.trigger_minute,
			'timerSchedule': self.timer_schedule,
			'programToLaunch': self.program_to_launch,
			'arguments': self.arguments
		}
		
		return resp
	
	def to_json(self):
		resp = self.to_storage_json()
		resp['timerSchedule'] = [self.num_to_dow(x) for x in self.timer_schedule]
		
		return resp
		
	def save_to_cron(self):
		# first see if this is new or update
		found_cron = False
		for job in cron:
			if job.comment == self.timer_id:
				# we found a matching record so just update item
				found_cron = True
				self.set_cron_record(job)
				break
				
		if not found_cron:
			job = cron.new(command='test')
			self.set_cron_record(job)

		cron.write()
	
	def set_cron_record(self, job):
		app.logger.info(self.to_storage_json())
		arg_string = ''
		if self.arguments is not None:
			arg_list = []
			for name, value in self.arguments.iteritems():
				arg_list.append(name + "=" + str(value))
			arg_string = '?' + '&'.join(arg_list)
			
		job.comment = self.timer_id
		job.command = 'curl localhost:8081/programs/{}{}'.format(self.program_to_launch, arg_string)
		job.minute.on(self.trigger_minute)
		job.hour.on(self.trigger_hour)
		job.dow.on(*self.timer_schedule)
	
	def delete_from_cron(self):
		cron.remove_all(comment=self.timer_id)
		cron.write()
		

@api.resource('/stop-program')
class StopProgramController(Resource):
	# stop currently executing program
	def get(self):
		try:
			global PROGRAM_PROCESS
			app.logger.info('Handling GET request on /stop-program endpoint')
			try:
				if PROGRAM_PROCESS.is_alive():
					current = PROGRAM_PROCESS.current_program
					QUIT.set()
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
	'''Get current program'''
	
	def get(self):
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
	valid_programs = ["wakeup", "wakeup_demo", "single_color", "full_wash", "blackout"]
	
	# run a program
	def get(self, program):
		try:
			app.logger.info('Handling GET request on /programs/{} endpoint'.format(program))
			if program not in ProgramAPI.valid_programs:
				return {"error": "{} is not a recognized program".format(program)}, 404
				
			global PROGRAM_PROCESS
				
			# get the dict of url arguments in case they are needed
			query_dict = request.args.to_dict()
			
			# kill any existing program process because we will create a new one shortly
			try:
				if PROGRAM_PROCESS.is_alive():
					QUIT.set()
					PROGRAM_PROCESS.join()
					PROGRAM_PROCESS = None
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
					return { "error": "red, green, and blue values are required and must be integers between 0 and 255." }, 400
				
				PROGRAM_PROCESS = SingleColorProgram(QUIT, red, green, blue)
				PROGRAM_PROCESS.start()
					
					
			elif program == 'blackout':
				PROGRAM_PROCESS = BlackoutProgram(QUIT)
				PROGRAM_PROCESS.start()
				
				
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
				
				if multiplier is None:
					PROGRAM_PROCESS = WakeupProgram(QUIT)
				else:
					PROGRAM_PROCESS = WakeupProgram(QUIT, multiplier)
				
				PROGRAM_PROCESS.start()
			
			
			elif program == 'wakeup_demo':
				PROGRAM_PROCESS = WakeupProgram(QUIT, 1)
				PROGRAM_PROCESS.start()
				
			return {}, 200
			
		except Exception:
			app.logger.error("Error handling request", exc_info=True)
			return { "error": "Error handling request." }, 500

class ColorObject(object):
	def __init__(self, r, g, b):
		self.r = r
		self.g = g
		self.b = b

class BaseProgram(multiprocessing.Process):
	def __init__(self, quit_event):
		super(BaseProgram, self).__init__()
		self.daemon = True
		
		self.quit_event = quit_event
		self.strip = rpi.PixelStrip(NUM_PIXELS, 10)
		self.strip.begin()
	
	def exit_gracefully(self):
		app.logger.info('Stopping current program during process shutdown')
		self.quit_event.clear()
		self.blackout()
		self.strip._cleanup()
		self.current_program = None
	
	def blackout(self):
		data = [ColorObject(0,0,0) for i in range(NUM_PIXELS)]
		for i in range(0,5):
			self.send_data(data)
			sleep(.05)
			
	def send_data(self, data):
		for i in range(0,len(data)):
			# note the ordering of RBG in the mapping. Not sure how to make the library do tha that for me in the PixelStrip function
			self.strip.setPixelColorRGB(i,data[i].r, data[i].b, data[i].g)
		
		self.strip.show()

		
class BlackoutProgram(BaseProgram):
	def __init__(self, quit_event):
		super(BlackoutProgram, self).__init__(quit_event)
		self.current_program = 'blackout'
		
	def run(self):
		app.logger.info('Starting BlackoutProgram')
		self.exit_gracefully()
		
		
class SingleColorProgram(BaseProgram):
	
	def __init__(self, quit_event, red=0, green=0, blue=0):
		super(SingleColorProgram, self).__init__(quit_event)
		self.red = red
		self.green = green
		self.blue = blue
		self.current_program = 'single_color'
		
		
	def run(self):
		app.logger.info('Starting SingleColorProgram with rgb = {}, {}, {}'.format(str(self.red), str(self.green), str(self.blue)))
		r = self.red
		g = self.green
		b = self.blue
		data = [ ColorObject(r, g, b) for i in range(NUM_PIXELS)]
		
		while not self.quit_event.is_set():
			self.send_data(data)
			sleep(.1)
		
		self.exit_gracefully()
		

class FullWashProgram(BaseProgram):
	
	# r, g, b
	program_options = [
		(255,0,255),	# pink
		(128,0,255),	# purple
		(255,0,128),	# bright pink
		(0,255,255),	# teal
		(0,255,128),	# green teal
		(0,128,255),	# blue teal
		(255,0,0),		# red
		(0,255,0),		# green
		(0,0,255)		# blue
	]
	
	def __init__(self, quit_event):
		super(FullWashProgram, self).__init__(quit_event)
		self.transition_cycles = 10
		self.current_program = 'full_wash'
		
	def run(self):
		app.logger.info('Starting FullWashProgram')
		while not self.quit_event.is_set():
			self.send_data(data)
			sleep(.1)
		
				
		
class WakeupProgram(BaseProgram):
	
	# r, g, b, led pct, transition time ratio from this to next,
	program_sequence = [
		(0,0,0,10,1),	# black
		(0,0,10,15,1),	# dark blue
		(2,0,15,20,1),	# purple
		(7,0,10,25,1),	# reddish purple
		(20,1,0,30,1),	# blood orange
		(50,6,0,40,1),	# orange
		(70,15,0,50,1),	# yellow
		(70,15,2,60,2),	# warm white
		(255,200,100,100,5), # white
		(255,200,100,100,0)	# white
	]

	def __init__(self, quit_event, multiplier=30):
		super(WakeupProgram, self).__init__(quit_event)
		self.base_multiplier = 60
		self.multiplier = multiplier
		if self.multiplier == 1:
			self.current_program = 'wakeup_demo'
		else:
			self.current_program = 'wakeup'
	
	def _calc_deltas(self, from_state, to_state):
		red_delta = self._calc_delta(to_state[0], from_state[0])
		green_delta = self._calc_delta(to_state[1], from_state[1])
		blue_delta = self._calc_delta(to_state[2], from_state[2])
		pixel_delta = (float(to_state[3])/100.0 * float(NUM_PIXELS)) - (float(from_state[3])/100.0 * float(NUM_PIXELS))
		
		return red_delta, green_delta, blue_delta, pixel_delta
		
	def _calc_delta(self, to_item, from_item):
		return float(to_item - from_item)
		
	def _calc_delta_influence(self, delta, iter_count, j):
		return int(round(float(delta) * (float(j) / float(iter_count))))
		
		
	def run(self):
		app.logger.info('Starting WakeupProgram with multiplier={}'.format(str(self.multiplier)))
		data = [ColorObject(0,0,0) for x in range(0,NUM_PIXELS)]
		for i in range(1, len(WakeupProgram.program_sequence)):
			
			from_state = WakeupProgram.program_sequence[i-1]
			to_state = WakeupProgram.program_sequence[i]
			app.logger.info(str(i))
			app.logger.info(from_state)
			
			red_delta, green_delta, blue_delta, pixel_delta = self._calc_deltas(from_state, to_state)
			
			iter_count = self.multiplier * self.base_multiplier * from_state[4]
			app.logger.info("iter_count = " + str(iter_count))
			app.logger.info("deltas: ")
			app.logger.info((red_delta, green_delta, blue_delta, pixel_delta))
			for j in range(0, iter_count):
				# app.logger.info("j = " + str(j))
				red = from_state[0] + self._calc_delta_influence(red_delta, iter_count, j)
				green = from_state[1] + self._calc_delta_influence(green_delta, iter_count, j)
				blue = from_state[2] + self._calc_delta_influence(blue_delta, iter_count, j)
				pixel_count = int(round(float(from_state[3])/100.0*NUM_PIXELS)) + self._calc_delta_influence(pixel_delta, iter_count, j)
				# app.logger.info(str(pixel_count) + " " + str(pixel_delta))
				
				# set unused pixels to black
				
				for idx in range(pixel_count, NUM_PIXELS):
					data[idx] = ColorObject(0,0,0)
				
				try:
					# set used pixels to correct color
					for k in range(0, pixel_count):
						data[k] = ColorObject(red, green, blue)
				except Exception as e:
					app.logger.info(str(k))
					app.logger.info(str(pixel_count))
					app.logger.info(str(pixel_delta))
					app.logger.info(str(NUM_PIXELS) + '\n')
					
					raise e
					
				self.send_data(data)
				sleep(.1)
				
		self.exit_gracefully()
	
	
	
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
		
if __name__ == "__main__":
	app.run(host='0.0.0.0', port=8081)