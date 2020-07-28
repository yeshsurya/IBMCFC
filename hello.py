from cloudant import Cloudant
from flask import Flask, render_template, request, jsonify,Blueprint,redirect,url_for
from forms import LoginForm, RegisterForm, DisasterUpdateForm 
import atexit
import os
import json
from flask_googlemaps import GoogleMaps, Map, icons
from dynaconf import FlaskDynaconf
import requests 

app = Flask(__name__, static_url_path='',template_folder='static')
GoogleMaps(app)
FlaskDynaconf(app)

db_name = 'mydb'
client = None
db = None

if 'VCAP_SERVICES' in os.environ:
    vcap = json.loads(os.getenv('VCAP_SERVICES'))
    print('Found VCAP_SERVICES')
    if 'cloudantNoSQLDB' in vcap:
        creds = vcap['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)
elif "CLOUDANT_URL" in os.environ:
    client = Cloudant(os.environ['CLOUDANT_USERNAME'], os.environ['CLOUDANT_PASSWORD'], url=os.environ['CLOUDANT_URL'], connect=True)
    db = client.create_database(db_name, throw_on_exists=False)
elif os.path.isfile('vcap-local.json'):
    with open('vcap-local.json') as f:
        vcap = json.load(f)
        print('Found local VCAP_SERVICES')
        creds = vcap['services']['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
        client = Cloudant(user, password, url=url, connect=True)
        db = client.create_database(db_name, throw_on_exists=False)

# On IBM Cloud Cloud Foundry, get the port number from the environment variable PORT
# When running this app on the local machine, default the port to 8000
port = int(os.getenv('PORT', 8000))

app.config['SECRET_KEY'] = 'any secret string'

users_blueprint = Blueprint(
    'users', __name__,
    template_folder='static'
)   # pragma: no cover


@app.route('/',methods=['GET','POST'])
def login():
    error = None
    import os 
    #SECRET_KEY = os.urandom(32)
    #app.config['SECRET_KEY'] = SECRET_KEY
    form=LoginForm(request.form)
    if (request.method=='POST'):
        if (request.form['username'] != 'admin' or request.form['password'] != 'admin'):
            error="Invalid credentials. Please try again."
        else:
            return redirect(url_for('root'))
    return render_template('login.html',form=form,error=error)

@app.route('/desc',methods=['GET','POST'])
def desc():   
    severityOps = ['Critical', 'Medium', 'Low']
    form=DisasterUpdateForm(request.form)
    if (request.method=='POST'):
        response = requests.post(url="api_url", json=form)
        return redirect(url_for('root'))    
    return render_template('disaster_desc.html',form=form,severityOps=severityOps)    

@app.route('/map')
def root():
    gmap = Map(
        identifier="gmap",
        varname="gmap",
        lat=37.4419,
        lng=-122.1419,
        markers={
            icons.dots.green: [(37.4419, -122.1419), (37.4500, -122.1350)],
            icons.dots.blue: [(37.4300, -122.1400, "Hello World")],
        },
        style="height:600px;width:1330px;margin:0;",
    )
    return render_template("simple.html", gmap=gmap)
    #return app.send_static_file('index.html')

# /* Endpoint to greet and add a new visitor to database.
# * Send a POST request to localhost:8000/api/visitors with body
# * {
# *     "name": "Bob"
# * }
# */
@app.route('/api/visitors', methods=['GET'])
def get_visitor():
    if client:
        return jsonify(list(map(lambda doc: doc['name'], db)))
    else:
        print('No database')
        return jsonify([])

# /**
#  * Endpoint to get a JSON array of all the visitors in the database
#  * REST API example:
#  * <code>
#  * GET http://localhost:8000/api/visitors
#  * </code>
#  *
#  * Response:
#  * [ "Bob", "Jane" ]
#  * @return An array of all the visitor names
#  */
@app.route('/api/visitors', methods=['POST'])
def put_visitor():
    user = request.json['name']
    data = {'name':user}
    if client:
        my_document = db.create_document(data)
        data['_id'] = my_document['_id']
        return jsonify(data)
    else:
        print('No database')
        return jsonify(data)

@atexit.register
def shutdown():
    if client:
        client.disconnect()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
