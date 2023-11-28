from flask import Flask
app = Flask(__name__)

@app.get('/log_derivation')
def list_log_derivation():
   return '{"result":"ok}'

@app.get('/log_service_call')
def list_log_service_call():
   return '{"result":"ok}'

if __name__ == '__main__':
    app.run(debug=True, port=8001)
