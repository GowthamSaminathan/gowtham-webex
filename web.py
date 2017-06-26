from flask import Flask, render_template, request
from flask import jsonify
import json
import MySQLdb
import os,time
#import pymongo
import datetime
from flask_pymongo import PyMongo

app = Flask(__name__,static_url_path='/static')
app.config['MONGO_DBNAME'] = 'LIVE'
app.config['MONGO_URI'] = 'mongodb://127.0.0.1:27017/LIVE'
mongoc = PyMongo(app)


									 
def sqlget_input(INID=0,GETNEW=True):
		try:
			# connect to LIVE database
			mdb = mongoc.db
			if GETNEW == True:
				# Get New INID from SESSION TABLE
				mcollection = mdb['SESSION']
				sesout = mcollection.find_one({"_id":1})
				INID = sesout.get("INID")
			
			mcollection = mdb['INPUT']
			all_data = mcollection.find({"INID":INID},{"_id":0})
			return list(all_data)
		except Exception as e:
				print "Error sqlget_byid>",e

def sqlget_output(SESSION=0,INID=0,LIVE=True):
		try:
				# connect to LIVE database
				mdb = mongoc.db
				if LIVE == True:
						# GET LIVE ID
						mcollection = mdb['SESSION']
						sesout = mcollection.find_one({"_id":1})
						INID = sesout.get("INID")
				
				mcollection = mdb['OUTPUT']
				all_data = mcollection.find({"INID":INID,"SESSION":SESSION},{"_id":0})
				return list(all_data)
		except Exception as e:
				print "Error sqlget_output",e


@app.route('/')
def main():
	 return render_template('index.html')

@app.route('/history',methods = ['POST', 'GET'])
def history():
		try:
				darray = []
				result = request.form
				print result
				# connect to LIVE database
				mdb = mongoc.db
				start = result.get("time1")
				end = result.get("time2")
				if start != None and end != None:
					start = datetime.datetime.strptime(start, "%d-%m-%Y %H:%M:%S")
					end = datetime.datetime.strptime(end, "%d-%m-%Y %H:%M:%S")
				
				if result["type"] == "count":
					#print result["type"]
					#print result["time1"]
					#print result["time2"]
					mcollection = mdb['OUTPUT']
					all_data = mcollection.count({"TD":{'$lt': end, '$gte': start}})
					darray.append( {"SESSION":all_data} )

				elif result["type"] == "timerange":
					mcollection = mdb['OUTPUT']
					all_data = mcollection.find({"TD":{'$lt': end, '$gte': start}},{"_id":0,"SESSION":1,"ID":1,"OUT":1,"TD":1})
					darray.append(list(all_data))
				
				elif result["type"] == "session":
						mcollection = mdb["OUTPUT"]
						all_data = mcollection.find({"SESSION":int(result["session"]),"INID":int(result["input"])},{"_id":0,"SESSION":1,"ID":1,"OUT":1,"TD":1})
						darray.append(list(all_data))
				
				elif result["type"] == "sessionrange":
						mcollection = mdb['OUTPUT']
						all_data = mcollection.find({"TD":{'$lt': end, '$gte': start}},{"_id":0,"SESSION":1,"INID":1})
						darray.append(list(all_data))
				
				elif result["type"] == "back":
					tim = result["time"]
					mcollection = mdb['OUTPUT']
					qr = mcollection.find({"TD":{"$lte":datetime.datetime.strptime(tim, "%d-%m-%Y %H:%M:%S")}},{"_id":0,"SESSION":1,"INID":1,"TD":1}).sort([("TD",-1)]).limit(1)
					qr = list(qr)
					if len(qr) > 0:
						qr = qr[0]
						all_data = mcollection.find({"SESSION":qr.get("SESSION"),"INID":qr.get("INID")},{"_id":0,"SESSION":1,"ID":1,"OUT":1,"TD":1})
						darray.append(list(all_data))

				elif result["type"] == "forward":
					tim = result["time"]
					mcollection = mdb['OUTPUT']
					qr = mcollection.find({"TD":{"$gte":datetime.datetime.strptime(tim, "%d-%m-%Y %H:%M:%S")}},{"_id":0,"SESSION":1,"INID":1,"TD":1}).sort([("TD",1)]).limit(1)
					qr = list(qr)
					if len(qr) > 0:
						qr = qr[0]
						all_data = mcollection.find({"SESSION":qr.get("SESSION"),"INID":qr.get("INID")},{"_id":0,"SESSION":1,"ID":1,"OUT":1,"TD":1})
						darray.append(list(all_data))

				return jsonify(darray)
		except Exception as e:
				print "Error history >",e
				return "None"

@app.route('/update',methods = ['POST', 'GET'])
def update():
		try:
				result = request.form
				if request.method == 'POST':
						if result["update"] != None:
								open("LIVE_UPDATE.txt",'wb+').write(result["update"])
								return "success"
		except Exception as e:
				print "Error update >",e
				return "None"


@app.route('/api',methods = ['POST', 'GET'])
def result():
	 dinput = 0
	 doutput = 0
	 draw = 0
	 if request.method == 'POST':
			result = request.form
			in_update = int(result.get("INID"))
			out_update = int(result.get("SESSION"))
			history = result.get("history")

			if history != None:
				h_time = result.get("time")
				mdb = mongoc.db
				mcollection = mdb['OUTPUT']
				iin_update = in_update
				oout_update = out_update
				
				if (iin_update == 0 or oout_update == 0):
					iin_update = -1
					oout_update = -1
				
				if history == "back":
					#find({"$and":[{"TD":{"$lte":datetime.datetime.fromtimestamp(float(h_time))}}]},{"_id":0,"SESSION":1,"INID":1,"TD":1}).sort([("TD",-1)]).limit(1)
					qr = mcollection.find({ "$or" : [ { "INID" : {"$ne": int(iin_update)} }, { "SESSION" : {"$ne": int(oout_update)} } ] ,"TD":{"$lte":datetime.datetime.strptime(h_time, "%d-%m-%Y %H:%M:%S")-datetime.timedelta(minutes=330)}}).sort([("TD",-1)]).limit(1)
					qr = list(qr)
					if len(qr) > 0:
						qr = qr[0]
						INID = int(qr.get("INID"))
						SESSION = int(qr.get("SESSION"))
						dinput = sqlget_input(INID,GETNEW=False)
						doutput = sqlget_output(SESSION,INID,LIVE=False)
						in_update = INID
						out_update = SESSION
					else:
						return "None"
				
				elif history == "forward":
					qr = mcollection.find({ "$or" : [ { "INID" : {"$ne": int(iin_update)} }, { "SESSION" : {"$ne": int(oout_update)} } ] ,"TD":{"$gte":datetime.datetime.strptime(h_time, "%d-%m-%Y %H:%M:%S")-datetime.timedelta(minutes=330)}}).sort([("TD",1)]).limit(1)
					qr = list(qr)
					if len(qr) > 0:
						qr = qr[0]

						INID = int(qr.get("INID"))
						SESSION = int(qr.get("SESSION"))
						dinput = sqlget_input(INID,GETNEW=False)
						doutput = sqlget_output(SESSION,INID,LIVE=False)
						in_update = INID
						out_update = SESSION
					else:
						return "None"

				else:

					return "None"

			else:

				#mongoc = pymongo.MongoClient('localhost', 27017)
				# connect to LIVE database
				mdb = mongoc.db
				mcollection = mdb['SESSION']
				sesout = mcollection.find_one({"_id":1})
				INID = int(sesout.get("INID"))
				SESSION = int(sesout.get("SESSION"))

				if in_update == 0 or INID != int(in_update):
						# INPUT NEW UPDATE REQUIRED
						in_update = INID
						dinput = sqlget_input(INID,GETNEW=False)
				else:
						# Client side INPUT is uptodate ( Not required to update input data )
						dinput = 0
				if out_update == 0 or SESSION != int(out_update):
						doutput = sqlget_output(SESSION,INID,LIVE=False)
						out_update = SESSION

			if dinput != 0 and doutput != 0 or int(result.get("INID")) != int(in_update):
				draw = open("LIVE_UPDATE.txt",'r').read()
			
			
			return jsonify({"input":dinput,"output": doutput,"in_update":in_update,"out_update":out_update,"draw":draw})
			
	 if request.method == 'GET':
			return jsonify(sqlget_output("0"))

if __name__ == '__main__':
	 app.run(host="0.0.0.0", port=int("8888"), debug=True)