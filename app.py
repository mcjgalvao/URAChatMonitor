from flask import Flask, jsonify, request
import json
import logging as log
import datetime
import sys
import time as ptime

from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app, Counter, Histogram

PRODUCTION = True
arg_list = sys.argv[1:]
for arg in arg_list:
   if arg == "--dev":
      PRODUCTION = False
   elif arg == "--help":
      print("Usage: python app.py [--dev]")
      sys.exit()

# Configure root logging engine 
root = log.getLogger()
root.setLevel(log.DEBUG if PRODUCTION else log.DEBUG)
log.basicConfig(format='%(asctime)s.%(msecs)03d|%(levelname)s|%(message)s', datefmt='%Y%m%d %H%M%S')
#log.basicConfig(filename='./log/test_log.txt', encoding='utf-8', level=log.DEBUG)
#root.addHandler(log.StreamHandler(sys.stdout))

# Create log file that will be sent to Loki for monitoring
#formatter = log.Formatter('%(asctime)s.%(msecs)03d|%(levelname)s|%(message)s')
#handler = log.FileHandler('./log/monitor_log.txt')
#handler.setFormatter(formatter)
#loki_log = log.getLogger("monitor_log")
#loki_log.setLevel(log.INFO)
#loki_log.addHandler(handler)
LOKI_SEP="|"

# Create de App
app = Flask(__name__)

# Create Metrics
c_start_total = Counter('log_start_total', 'Total number of requests for the log_start service'
                        , ['consumer','flow','brand','node'])

c_end_total = Counter('log_end_total', 'Total number of requests for the log_end service'
                      , ['consumer','flow','brand','node',"close_status","derived_to"]) 
h_interaction_duration = Histogram('log_interaction_duration', 'URA/ChatBot total interaction duration'
                                   , ['consumer','flow','brand','node','close_status','derived_to'])
# c_derivation_total = Counter('log_derivation_total', 'Total number of requests for the log_derivation service', ['consumer','flow','brand','node','derived_to'])

c_service_call_total = Counter('log_service_call_total', 'Total number of requests for the log_service_call service'
                               , ['consumer','flow','brand','node','service','result_code','timeout'])
h_service_call_duration = Histogram('log_service_call_duration', 'Perceived service time from consumers perspective'
                               , ['consumer','flow','brand','node','service','result_code','timeout'])

# internal metrics
c_internal_success = Counter('log_internal_success', 'Total number of successful requests'
                               , ['service'])
c_internal_error = Counter('log_internal_error', 'Total number of failed requests'
                               , ['service'])
h_internal_duration = Histogram('log_internal_duration', 'Internal service processing time'
                               , ['service'])

# CONSTANTS
CLOSE_DERIVED = "derived"
LOG_START_SERVICE = "log_start"
LOG_END_SERVICE = "log_end"
LOG_SERVICE_CALL_SERVICE = "log_service_call"

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

@app.route('/log_start', methods=['POST','GET','PUT'])
def register_start():
   global c_start_total
   global c_internal_success
   global c_internal_error
   global h_internal_duration
   global LOG_START_SERVICE
   global root

   start_time = ptime.time()

   SVC = LOG_START_SERVICE

   record = json.loads(request.data)
   app.logger.debug("/" + SVC +  ": " + str(record))

   try:
      consumer = record['consumer']
      #app.logger.debug("consumer: " + consumer)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'consumer' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'consumer\' field'})

   try:
      flow = record['flow']
      #app.logger.debug("flow: " + flow)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'flow' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'flow\' field'})

   try:
      brand = record['brand']
      #app.logger.debug("brand: " + brand)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'brand' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'brand\' field'})

   try:
      node = record['node']
      #app.logger.debug("node: " + node)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'node' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'node\' field'})

   try:
      time = record['time']
      #log.debug("time: " + time)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'time' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'time\' field'})

   # Process prometheus metrics
   c_start_total.labels(consumer=consumer,flow=flow,brand=brand,node=node).inc()
   c_internal_success.labels(service=SVC).inc()

   # Generate log line that will be parsed by Loki
   #loki_log.info("log_start" + LOKI_SEP + consumer + LOKI_SEP + flow + LOKI_SEP + brand + LOKI_SEP + node + LOKI_SEP + time)
   timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%Z")

   f_delta = ptime.time() - start_time
   h_internal_duration.labels(service=SVC).observe(f_delta)
   return jsonify({'result': 'ok',
                       'timestamp': timestamp})

@app.route('/log_end', methods=['POST','GET','PUT'])
def register_end():
   global c_end_total
   global h_interaction_duration
   global c_internal_success
   global c_internal_error
   global h_internal_duration
   global LOG_END_SERVICE

   start_time = ptime.time()

   SVC = LOG_END_SERVICE

   record = json.loads(request.data)
   app.logger.debug("/" + SVC + ": " + str(record))

   try:
      consumer = record['consumer']
      #app.logger.debug("consumer: " + consumer)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'consumer' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'consumer\' field'})

   try:
      flow = record['flow']
      #app.logger.debug("flow: " + flow)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'flow' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'flow\' field'})

   try:
      brand = record['brand']
      #app.logger.debug("brand: " + brand)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'brand' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'brand\' field'})

   try:
      node = record['node']
      #app.logger.debug("node: " + node)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'node' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'node\' field'})

   try:
      close_status = record['close-status']
      #app.logger.debug("close-status: " + close_status)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'close-status' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'close-status\' field'})
   try:
      derived_to = record['derived-to']
      #app.logger.debug("derived-to: " + derived_to)
   except KeyError:
      derived_to = ""
      if close_status == CLOSE_DERIVED:
         app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'derived-to' field. Mandatory when close-status==" + CLOSE_DERIVED)
         c_internal_error.labels(service=SVC).inc()
         return jsonify({'result': 'error',
                     'description': 'Missing \'derived-to\' field'})

   try:
      s_interaction_start_time = record['interaction-start-time']
      t_interaction_start_time = datetime.datetime.strptime(s_interaction_start_time,"%Y-%m-%d %H:%M:%S")
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'interaction-start-time' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'interaction-start-time\' field'})
   except ValueError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Bad String for 'interaction-start-time' field. Should be a 'YYYY-MM-DD hh:mm:ss'")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Bad String for \'interaction-start-time\' field. Should be a \'YYYY-MM-DD hh:mm:ss\''})

   try:
      s_interaction_end_time = record['interaction-end-time']
      t_interaction_end_time = datetime.datetime.strptime(s_interaction_end_time,"%Y-%m-%d %H:%M:%S")
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'interaction-end-time' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'interaction-end-time\' field'})
   except ValueError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Bad String for 'interaction-end-time' field. Should be a 'YYYY-MM-DD hh:mm:ss'")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Bad String for \'interaction-end-time\' field. Should be a \'YYYY-MM-DD hh:mm:ss\''})

   #app.logger.debug("interaction-start-time: " + s_interaction_start_time)
   #app.logger.debug("interaction-end-time: " + s_interaction_end_time)
   t_interaction_duration = t_interaction_end_time - t_interaction_start_time
   f_interaction_duration = t_interaction_duration.total_seconds()
   #app.logger.debug("f_interaction_duration: " + str(f_interaction_duration))

   try:
      time = record['time']
      #app.logger.debug("time: " + time)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'time' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'time\' field'})

   # Process prometheus metrics
   c_end_total.labels(consumer=consumer,flow=flow,brand=brand,node=node,close_status=close_status,derived_to=derived_to).inc()
   h_interaction_duration.labels(consumer=consumer,flow=flow,brand=brand,node=node,close_status=close_status,derived_to=derived_to).observe(f_interaction_duration)
   c_internal_success.labels(service=SVC).inc()

   # Generate log line that will be parsed by Loki
   #loki_log.info("log_end" + LOKI_SEP + consumer + LOKI_SEP + flow + LOKI_SEP + brand + LOKI_SEP + node + LOKI_SEP + close_status + LOKI_SEP + time)
   timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%Z")

   f_delta = ptime.time() - start_time
   h_internal_duration.labels(service=SVC).observe(f_delta)
   return jsonify({'result': 'ok',
                       'timestamp': timestamp})

@app.route('/log_service_call', methods=['POST','GET','PUT'])
def register_service_call():
   global c_service_call_total
   global h_service_call_duration
   global c_internal_success
   global c_internal_error
   global h_internal_duration
   global LOG_SERVICE_CALL_SERVICE

   start_time = ptime.time()

   SVC = LOG_SERVICE_CALL_SERVICE

   record = json.loads(request.data)
   app.logger.debug("/" + SVC + ": " + str(record))

   try:
      consumer = record['consumer']
      #app.logger.debug("consumer: " + consumer)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'consumer' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'consumer\' field'})

   try:
      flow = record['flow']
      #app.logger.debug("flow: " + flow)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'flow' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'flow\' field'})

   try:
      brand = record['brand']
      #app.logger.debug("brand: " + brand)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'brand' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'brand\' field'})

   try:
      node = record['node']
      #app.logger.debug("node: " + node)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'node' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'node\' field'})
  
   try:
      service = record['service']
      #app.logger.debug("service: " + service)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'service' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'service\' field'})

   try:
      result_code = record['result-code']
      #app.logger.debug("result-code: " + result_code)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'result-code' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'result-code\' field'})

   try:
      s_service_call_start_time = record['service-call-start-time']
      t_service_call_start_time = datetime.datetime.strptime(s_service_call_start_time,"%Y-%m-%d %H:%M:%S")
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'service-call-start-time' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'service-call-start-time\' field'})
   except ValueError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Bad String for 'service-call-start-time' field. Should be a 'YYYY-MM-DD hh:mm:ss'")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Bad String for \'service-call-start-time\' field. Should be a \'YYYY-MM-DD hh:mm:ss\''})

   try:
      s_service_call_end_time = record['service-call-end-time']
      t_service_call_end_time = datetime.datetime.strptime(s_service_call_end_time,"%Y-%m-%d %H:%M:%S")
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'service-call-end-time' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'service-call-end-time\' field'})
   except ValueError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Bad String for 'service-call-end-time' field. Should be a 'YYYY-MM-DD hh:mm:ss'")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Bad String for \'service-call-end-time\' field. Should be a \'YYYY-MM-DD hh:mm:ss\''})

   #app.logger.debug("service-call-start-time: " + s_service_call_start_time)
   #app.logger.debug("service-call-end-time: " + s_service_call_end_time)
   t_duration = t_service_call_end_time - t_service_call_start_time
   f_duration = t_duration.total_seconds()
   #app.logger.debug("f_duration: " + str(f_duration))

   try:
      timeout = record['timeout']
      #app.logger.debug("timeout: " + timeout)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'timeout' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'timeout\' field'})

   try:
      time = record['time']
      #app.logger.debug("time: " + time)
   except KeyError:
      app.logger.error("/" + SVC + ": " + str(record) + " -> Missing 'time' field")
      c_internal_error.labels(service=SVC).inc()
      return jsonify({'result': 'error',
                       'description': 'Missing \'time\' field'})

   # Process prometheus metrics
   c_service_call_total.labels(consumer=consumer,flow=flow,brand=brand,node=node,service=service,result_code=result_code,timeout=timeout).inc()
   h_service_call_duration.labels(consumer=consumer,flow=flow,brand=brand,node=node,service=service,result_code=result_code,timeout=timeout).observe(f_duration)
   c_internal_success.labels(service=SVC).inc()

   # Generate log line that will be parsed by Loki
   #loki_log.info("log_service_call" + LOKI_SEP + consumer + LOKI_SEP + flow + LOKI_SEP + brand + LOKI_SEP + node 
   #              + LOKI_SEP + service + LOKI_SEP + result_code 
   #              + LOKI_SEP + duration + LOKI_SEP + timeout + LOKI_SEP + time)
   timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%Z")
   
   f_delta = ptime.time() - start_time
   h_internal_duration.labels(service=SVC).observe(f_delta)
   return jsonify({'result': 'ok',
                       'timestamp': timestamp})

# for waitress
def create_app():
   return app

if __name__ == '__main__':
   if PRODUCTION:
      from waitress import serve
      serve(app, host="0.0.0.0", port=8001)
   else:
      app.run(debug=True, host="0.0.0.0", port=8001)


