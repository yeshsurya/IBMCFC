from cloudant import Cloudant
from flask import Flask, render_template, request, jsonify
from forms import LoginForm, RegisterForm 
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
def insert_into_db():
    #Assuming sample data to be the input
    #TODO: also get user name from login as a db field
    for data in sample_data:
        json_doc= {
            "latitude" : data[0], 
            "longitude" : data[1], 
            "danger" : data[2], 
            "description" : data[3]
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
    #Retrieval will be based on geolocation of user: lat,long
    # latitude: 0.001 degree = 111 m 
    lat = 5.989
    lon = -50.14
    selector = {
            'latitude': {
                '$gte': lat-0.0005, 
                '$lte' : lat+ 0.0005
                 } ,
             "longitude":  {
                 '$gte': lon-0.0005, 
                 '$lte' : lon+0.0005
                }
            } 
    qr= Query(db, selector=selector)
    query_res = qr(limit=1000, skip=0)['docs']
    
    # code to add into maps
    green_marker=[]
    red_marker=[]
    orange_marker=[]
    white_marker=[]
    for each in query_res:
        if (each['danger']=='Safe'): 
            green_marker.append((each['latitude'], each['longitude'], each['description']))
        elif (each['danger']=='Medium'): 
            orange_marker = (each['latitude'], each['longitude'], each['description'])
        elif (each['danger']=='High'):
            red_marker = (each['latitude'], each['longitude'], each['description'])
        else: 
            white_marker: (each['latitude'], each['longitude'], each['description'])
    #print(green_marker)

# todo : REMOVE SAMPLE DATA 
# Data structed as
# Latitude, Longitude, DangerLevel (Change to enum), Description
sample_data = [
    [3.8197, 37.4419, "High", "Electric pole fallen"],
    [3.98, -122.1400, "Medium", "xyz abdd"],
    [5.989 ,-50.1400, "Safe", "none"],
]

insert_into_db()
retrieve_from_db()


# On IBM Cloud Cloud Foundry, get the port number from the environment variable PORT
# When running this app on the local machine, default the port to 8000
port = int(os.getenv('PORT', 8000))
@app.route('/login',methods=['GET','POST'])
def login():
    error = None
    form=LoginForm(request.form)
    if (request.method=='POST'):
        if (request.form['username'] != 'admin' or request.form['password'] != 'admin'):
            error="Invalid credentials. Please try again."
        else:
            return redirect(url_for('map_created_in_view'))
    return render_template('login.html',form=form,error=error)        
@app.route('/')
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
    app.run(host='0.0.0.0', port=port, debug=True)
