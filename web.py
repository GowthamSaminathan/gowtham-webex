from flask import Flask, render_template, request , send_file
from flask import jsonify
from werkzeug.utils import secure_filename
import json
import MySQLdb
import os,time
#import pymongo
import datetime
from flask_pymongo import PyMongo
import glob
import net_auto
import shutil
from threading import Thread


# Create dummy thread
global main_thread
main_thread = Thread(target="",name="No")
main_thread.run()
main_thread.isAlive()

app = Flask(__name__,static_url_path='/static')
app.config['MONGO_DBNAME'] = 'LIVE'
app.config['MONGO_URI'] = 'mongodb://127.0.0.1:27017/LIVE'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(),"input_file")
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

@app.route('/upload_input',methods = ['POST', 'GET'])
def upload_input():
    if request.method == 'POST':
    	try:
        	f = request.files['file']
        	filename = secure_filename(f.filename)
        	print os.path.join(app.config['UPLOAD_FOLDER'])
        	f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        	return 'success'
        except Exception as e:
        	print e
        	return "failed"

@app.route('/job',methods = ['POST', 'GET'])
def get_job():
	global main_thread
	status = {"status":"error"}
	if request.method == 'POST':
		try:
			typ = request.form.get('type')
			if typ == "GetRunningJob":
				if main_thread.isAlive() == True:
					status = {"status":"Running","jobname":main_thread.getName()}
				else:
					status = {"status":"Not Running","jobname":main_thread.getName()}
			elif jn == "kill":
				if main_thread.isAlive() == True:
					jn = request.form.get('jobname')
					job_name = main_thread.getName()
					if jn == job_name:
						pass;
						# Killing is not possible in threading module
						#main_thread.kill()
					else:
						status = {"status":"No Job Found","jobname":jn}
				else:
					status = {"status":"Not Running","jobname":main_thread.getName()}
			return jsonify(status)
		except Exception as e:
			return jsonify({"status":"error"})

@app.route('/new_job',methods = ['POST', 'GET'])
def new_job():
	global main_thread
	status = {"status":"error"}
	if request.method == 'POST':
		try:
			fn = request.form.get('filename')
			jn = request.form.get('jobname')
			apr = request.form.get('apprentice')
			try:
				apr = int(apr)
				if apr < 1:
					apr = 5
			except:
				apr = 5
			if fn == None or jn == None:
				return jsonify(status)
			filename = secure_filename(fn)
			full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
			if os.path.isfile(full_path):
				# Schudle Job
				if main_thread.isAlive() == False:
					jn = jn+"-"+str(datetime.datetime.now().strftime("%d-%B-%H:%M:%S"))
					main_thread = Thread(target=net_auto_modul.main_run,name = jn, args=(full_path,jn,apr,))
					main_thread.start()
					status = {"status":"Job Started"}
				else:
					status = {"status":"ExistingJobRunning"}
			else:
				status = {"status":"InputFileNotFound"}
			return jsonify(status)
		except Exception as e:
			print e
			return jsonify({"status":"error"})

@app.route('/delete_input',methods = ['POST', 'GET'])
def delete_input():
    if request.method == 'POST':
    	try:
    		status = {"status":"Not Deleted"}
    		fn = request.form.get('filename')
        	full_path = os.path.join(app.config['UPLOAD_FOLDER'], fn)
        	try:
        		os.remove(full_path)
        		return jsonify({"status":"Deleted"})
        	except:
        		return jsonify(status)
        except Exception as e:
        	print e
        	return "failed"

@app.route('/download_input',methods = ['POST', 'GET'])
def download_input():
    if request.method == 'GET':
    	try:
    		dfile = request.args.get('download')
    		if dfile != None:
    			rf = os.path.join(os.getcwd(),"input_file")
    			fp = os.path.join(rf,dfile)
    			return send_file(fp, as_attachment=True)
        except Exception as e:
        	return "failed"

@app.route('/list_input',methods = ['POST', 'GET'])
def list_input():
    if request.method == 'POST':
    	try:
    		name = os.listdir(app.config['UPLOAD_FOLDER'])
    		if len(name) > 0:
    			return jsonify({"files":name})
    		else:
    			return "failed"
        except Exception as e:
        	return "failed"

@app.route('/rawdownload',methods = ['POST', 'GET'])
def rawdownload():
    if request.method == 'GET':
    	try:
    		rawfile = request.args.get('download')
    		if rawfile != None:
    			rf = os.path.join(os.getcwd(),"divlog")
    			rawfile = rawfile.replace(":","-")
    			fp = os.path.join(rf,rawfile)
    			if os.path.isfile(fp+".zip") == True:
    				pass;
    			else:
    				shutil.make_archive(fp,"zip",fp)
    			return send_file(fp+".zip", as_attachment=True)
        except Exception as e:
        	return "failed"


if __name__ == '__main__':
	net_auto_modul = net_auto.main_model()
	app.run(host="0.0.0.0", port=int("8888"), debug=True)