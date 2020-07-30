from cloudant import Cloudant
from flask import Flask, render_template, request, jsonify,Blueprint,redirect,url_for
from forms import LoginForm, RegisterForm, DisasterUpdateForm 
import atexit
import os
import json
from flask_googlemaps import GoogleMaps, Map, icons
from dynaconf import FlaskDynaconf
import re,requests
from cloudant.result import Result, ResultByKey
from cloudant.query import Query

app = Flask(__name__, static_url_path='',template_folder='static')
GoogleMaps(app)
FlaskDynaconf(app)

db_name = 'mydb'
client = None
db = None
latitude = 13.297813
longitude = 77.804075
load_count = 0
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


# /**
#  * Get data from form and insert into database
#  * 
#  * @return 
#  */
def insert_into_db(inputdata):
    #Assuming sample data to be the input
    #TODO: also get user name from login as a db field   
    global latitude
    global longitude
    json_doc= {
        "latitude" : latitude, 
        "longitude" : longitude, 
        "danger" : inputdata['sev'], 
        "description" : inputdata['description']
    }
    new_document = db.create_document(json_doc)
    if new_document.exists():
        print(f"Document '{new_document}' successfully created.")
    


# /**
#  * Retrieve database result and process into marker
#  * 
#  * @return 
#  */
def retrieve_from_db():
    # Retrieval will be based on geolocation of user: lat,long
    # latitude: 0.001 degree = 111 m 
    lat = 5.989
    lon = -50.14
    selector = {
            '_id': {
                '$gt': 0, 
                 } 
            } 
    #qr= Query(db, selector=selector)
    #query_res = qr(limit=1000, skip=0)['docs']
    query_res = Result(db.all_docs,include_docs=True)
    print("Query res is ")
    print(query_res)
    # code to add into maps
    green_marker=[]
    red_marker=[]
    orange_marker=[]
    white_marker=[]
    try:
        for ea in query_res:
            each = ea['doc']
            print(each)
            print(dir(each))
            if (each['danger']=='Low'): 
                green_marker.append((each['latitude'], each['longitude'], each['description']))
            elif (each['danger']=='Medium'): 
                orange_marker.append((each['latitude'], each['longitude'], each['description']))
            elif (each['danger']=='Critical'):
                red_marker.append((each['latitude'], each['longitude'], each['description']))
            else: 
                white_marker.append((each['latitude'], each['longitude'], each['description']))
    except:
        pass
    print("Green Marker is ")
    print(green_marker)    
    print("Orange Marker is")
    print(orange_marker)
    print("Red markers are")
    print(red_marker)
    return (green_marker,red_marker,orange_marker,white_marker)
    #print(green_marker)

# todo : REMOVE SAMPLE DATA 
# Data structed as
# Latitude, Longitude, DangerLevel (Change to enum), Description
sample_data = [
    [3.8197, 37.4419, "High", "Electric pole fallen"],
    [3.98, -122.1400, "Medium", "xyz abdd"],
    [5.989 ,-50.1400, "Safe", "none"],
]

#insert_into_db()
#retrieve_from_db()


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
        print(request.form['description'])
        print(request.form['sev'])
        print(request.form.to_dict())
        insert_into_db(request.form.to_dict())
        #response = requests.post(url="api_url", json=form)
        return redirect(url_for('root'))    
    return render_template('disaster_desc.html',form=form,severityOps=severityOps)    
#Javascript to get geolocation position
#navigator.geolocation.getCurrentPosition(function(position){console.log(position.coords.latitude)})
#navigator.geolocation.getCurrentPosition(function(position){console.log(position.coords.longitude)})
@app.route('/map',methods=['GET','POST'])
def root():
    green_marker,red_marker,orange_marker,white_marker  = retrieve_from_db()
    global latitude
    global longitude
    global load_count
    if(request.method=='POST'):
        print('printing request')
        inp_data = json.loads(request.get_data())
        latitude = inp_data['latitude']
        longitude = inp_data['longitude']
        if(load_count == 0):
            load_count = load_count + 1
            return "reload"
        else :
            return "success"
    else:
        gmap = Map(
            identifier="gmap",
            varname="gmap",
            lat=latitude,
            lng=longitude,
            markers={
                icons.dots.green: green_marker,
                icons.dots.red: red_marker,
                icons.dots.pink:orange_marker,
                icons.dots.purple:white_marker, 
                icons.dots.yellow:[(latitude,longitude,"You are here")]
            },
            style="height:600px;width:1330px;margin:0;",
        )
    return render_template("simple.html", gmap=gmap)
    #return app.send_static_file('index.html')
    #return render_template("location.html", mymap=gmap)


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
    app.run(host='0.0.0.0', port=port, debug=True,ssl_context='adhoc')
