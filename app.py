from flask import Flask, jsonify, request
import json
import logging as log
import datetime
import sys

from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app, Counter, Histogram

# Configure root logging engine 
root = log.getLogger()
root.setLevel(log.DEBUG)
#log.basicConfig(format='%(asctime)s.%(msecs)03d|%(levelname)s|%(message)s', datefmt='%Y%m%d %H%M%S')
log.basicConfig(filename='test_log.txt', encoding='utf-8', level=log.DEBUG)
root.addHandler(log.StreamHandler(sys.stdout))

# Create log file that will be sent to Loki for monitoring
formatter = log.Formatter('%(asctime)s %(levelname)s %(message)s')
handler = log.FileHandler('monitor_log.txt')
handler.setFormatter(formatter)
loki_log = log.getLogger("monitor_log")
loki_log.setLevel(log.INFO)
loki_log.addHandler(handler)

# Create de App
app = Flask(__name__)

# Create Metrics
c_derivation_total = Counter('log_derivation_total', 'Total number of requests for the log_derivation service', ['consumer','node','derived_to'])
c_service_call_total = Counter('log_service_call_total', 'Total number of requests for the log_service_call service', ['consumer','node','service','result_code','timeout'])
h_service_call_duration = Histogram('log_service_call_duration', 'Perceived service time from consumers perspective', ['consumer','node','service','result_code','timeout'])

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

@app.route('/log_derivation', methods=['POST','GET','PUT'])
def register_derivation():
   global c_derivation_total

   record = json.loads(request.data)
   log.debug("DATA IN: " + str(record))

   try:
      consumer = record['consumer']
      log.debug("consumer: " + consumer)
   except KeyError:
      log.error("Missing 'consumer' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'consumer\' field'})

   try:
      node = record['node']
      log.debug("node: " + node)
   except KeyError:
      log.error("Missing 'node' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'node\' field'})

   try:
      derived_to = record['derived-to']
      log.debug("derived-to: " + derived_to)
   except KeyError:
      log.error("Missing 'derived-to' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'derived-to\' field'})

   try:
      time = record['time']
      log.debug("time: " + time)
   except KeyError:
      log.error("Missing 'time' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'time\' field'})

   # Process prometheus metrics
   c_derivation_total.labels(consumer=consumer,node=node,derived_to=derived_to).inc()

   # Generate log line that will be parsed by Loki
   loki_log.info("log_derivation: " + consumer + " " + node + " " + derived_to + " " + time)
   timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%Z")

   return jsonify({'result': 'ok',
                       'timestamp': timestamp})

@app.route('/log_service_call', methods=['POST','GET','PUT'])
def register_service_call():
   record = json.loads(request.data)
   log.debug("DATA IN: " + str(record))

   try:
      consumer = record['consumer']
      log.debug("consumer: " + consumer)
   except KeyError:
      log.error("Missing 'consumer' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'consumer\' field'})

   try:
      node = record['node']
      log.debug("node: " + node)
   except KeyError:
      log.error("Missing 'node' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'node\' field'})

   try:
      service = record['service']
      log.debug("service: " + service)
   except KeyError:
      log.error("Missing 'service' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'service\' field'})

   try:
      result_code = record['result-code']
      log.debug("result-code: " + result_code)
   except KeyError:
      log.error("Missing 'result-code' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'result-code\' field'})

   try:
      duration = record['duration']
      f_duration = float(duration)
      log.debug("duration: " + duration)
   except KeyError:
      log.error("Missing 'duration' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'duration\' field'})
   except ValueError:
      log.error("Bad Type for 'duration' field. Should be a float number in seconds")
      return jsonify({'result': 'error',
                       'description': 'Bad Type for \'duration\' field. Should be a float number in seconds'})

   try:
      timeout = record['timeout']
      log.debug("timeout: " + timeout)
   except KeyError:
      log.error("Missing 'timeout' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'timeout\' field'})

   try:
      time = record['time']
      log.debug("time: " + time)
   except KeyError:
      log.error("Missing 'time' field")
      return jsonify({'result': 'error',
                       'description': 'Missing \'time\' field'})

   # Process prometheus metrics
   c_service_call_total.labels(consumer=consumer,node=node,service=service,result_code=result_code,timeout=timeout).inc()
   h_service_call_duration.labels(consumer=consumer,node=node,service=service,result_code=result_code,timeout=timeout).observe(f_duration)

   # Generate log line that will be parsed by Loki
   loki_log.info("log_service_call: " + consumer + " " + node + " " + service + " " + result_code 
      + " " + duration + " " + timeout + " " + time)
   timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%Z")

   return jsonify({'result': 'ok',
                       'timestamp': timestamp})
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8001)


