from flask import Flask
from flask import request
from flask import jsonify
from random import randint
import Data_Analysis as da
import json
import csv
import psycopg2
import datetime



# START:  Database setup    #

DB_NAME = "DeNachtwachtDB"
DB_USER = "postgres"
DB_PASS = "admin"
DB_HOST = "127.0.0.1"
DB_PORT = 5432

try:
    connection = psycopg2.connect(database = DB_NAME, user = DB_USER, password = DB_PASS, host = DB_HOST, port = DB_PORT)

    print("--- Server established connection with the database ---\n")

except:
    print("--- Server could not establish connection with database ---\n")

cursor = connection.cursor()


# END:    Database setup    #





# START:    http requests     #

app = Flask(__name__)


@app.route( '/user', methods = ["GET", "POST"] )
def registerUser():

    # GET requests are used to retreive al information about a user [args -> 'uid']
    if request.method == "GET":
        # out of request we can extract the arguments given in the http request (account details)
        userid = request.args.get('uid', None)

        cursor.execute(
            """select * from "Users" where uid = %s""", (userid,)
        )
        userinfo = cursor.fetchall()[0]
        usrdict = {"uid":userinfo[0], "username":userinfo[1], "password":userinfo[2], "csv":userinfo[3]}

        return usrdict

    # POST requests are used to store new user entries in the database
    if request.method == "POST":

        body = json.loads(request.data, strict=False)   # getting the body out of the post request
        username = body["username"]
        password = body["password"]

        # making a csv file to store incomming sleep data on
        csvFileName = username + '_' + str(randint(1000, 9999)) + '_sleepData.csv'

        with open(csvFileName, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['time', 'heartrate'])

        # storing user account details in database and refering the csv file linked to the account
        cursor.execute(
            """insert into "Users"(username, password, csvfilename) values(%s, %s, %s)""" , ( username, password, csvFileName )
        )
        connection.commit()

        # returning a succes response to the client
        return jsonify( succes = True ) # this is a generated 200 response to the client side


@app.route('/sleepdata', methods = ["GET", "POST"])
def sleepData():

    # Args      -> uid | size(Amount of data points)
    # Returns   -> JSON array of Time/Heartrate Tuples
    if request.method == "GET":
        user = request.args.get('uid', None)
        size = int(request.args.get('size', None))

        csvUser = getCsvForUser(user)

        with open(csvUser, 'r') as file:
            data = []
            csv_reader = list(reversed(list(csv.reader(file, delimiter=','))))
            line = 0
            while line < size and line < len(csv_reader) - 1:
                data.append(csv_reader[line])
                line += 1

        return json.dumps(data)

    # Post method uploads data to database for mentioned user
    if request.method == "POST":

        body = json.loads(request.data, strict=False)
        user = body["uid"]
        data = body["data"]

        csvUser = getCsvForUser(user)

        # Writing the new datapoints to csv file of user
        with open(csvUser, 'a', newline='') as file:
            writer = csv.writer(file)

            for row in data:
                writer.writerow([row[0], row[1]])

        # Analyzing new data to check if a 'wakeUp' response is needed
        with open(csvUser, 'r') as file:
            csvIterator = csv.reader(file, delimiter=',')
            next(csvIterator)
            dataPoints = list(csvIterator)[:100]

        heartrates = []
        for datapoint in dataPoints:
            heartrates.append(datapoint[1])
        dataForAnalysis = list(reversed(heartrates))

        analyseResult = da.analyseData(dataForAnalysis)

        res = json.dumps({ "succes" : True , "wakeup" : analyseResult})

        return res



# END:    http requests     #



# START:  global funcs      #

def getCsvForUser(user):
    # returns the path to the user's csv file

    cursor.execute("""select csvfilename from "Users" where uid = %s""", (user,))
    return str(cursor.fetchone()[0])


# END:   global funcs       #


if __name__ == '__main__':
    app.run()

