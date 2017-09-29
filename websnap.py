from flask import Flask, render_template, request , send_file
from flask import jsonify
from werkzeug.utils import secure_filename
import json
import os,time
#import pymongo
import datetime
from flask_pymongo import PyMongo
import glob
import MonitorEngine
import shutil
import pandas
import random
from threading import Thread
import logging
from logging.handlers import RotatingFileHandler


logger =  logging.getLogger("Rotating Log websnap")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(os.getcwd()+"/Websnap.log",maxBytes=5000000,backupCount=25)
formatter = logging.Formatter('%(asctime)s > %(levelname)s > %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
#logger.propagate = False # DISABLE LOG STDOUT

logger.info("Starting MonitoringEngine")

# Create dummy thread
global main_thread
main_thread = Thread(target="",name="No")
main_thread.run()
main_thread.isAlive()

app = Flask(__name__,static_url_path='/static')
app.config['MONGO_DBNAME'] = 'LIVE'
app.config['MONGO_URI'] = 'mongodb://127.0.0.1:27017/LIVE'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(),"input_file")
app.config['TEMP_FOLDER'] = os.path.join(os.getcwd(),"temp_file")
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
				logger.exception("sqlget_input")

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
				logger.exception("sqlget_output")


@app.route('/')
def main():
	 return render_template('index.html')

@app.route('/history',methods = ['POST', 'GET'])
def history():
		try:
				darray = []
				result = request.form
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
					all_data = mcollection.find({"TD":{'$lt': end, '$gte': start}},{"_id":0,"Authentication":0})
					darray.append(list(all_data))
				
				elif result["type"] == "session":
						mcollection = mdb["OUTPUT"]
						all_data = mcollection.find({"SESSION":int(result["session"]),"INID":int(result["input"])},{"_id":0,"Authentication":0})
						darray.append(list(all_data))
				
				elif result["type"] == "sessionrange":
						mcollection = mdb['OUTPUT']
						all_data = mcollection.find({"TD":{'$lt': end, '$gte': start}},{"_id":0,"SESSION":1,"INID":1})
						darray.append(list(all_data))
				
				elif result["type"] == "back":
					tim = result["time"]
					mcollection = mdb['OUTPUT']
					qr = mcollection.find({"TD":{"$lte":datetime.datetime.strptime(tim+".999999", "%d-%m-%Y %H:%M:%S.%f")}},{"_id":0,"Authentication":0}).sort([("TD",-1)]).limit(1)
					qr = list(qr)
					if len(qr) > 0:
						qr = qr[0]
						all_data = mcollection.find({"SESSION":qr.get("SESSION"),"INID":qr.get("INID")},{"_id":0,"Authentication":0})
						darray.append(list(all_data))

				elif result["type"] == "history_list":
					tim = result["time"]
					limit = int(result["limit"])
					mcollection = mdb['HISTORY']
					all_data = mcollection.find({"TD":{"$lte":datetime.datetime.strptime(tim+".999999", "%d-%m-%Y %H:%M:%S.%f")}},{"_id":0,"INID":1,"SESSION":1,"JOBNAME":1,"TD":1}).sort([("TD",-1)]).limit(limit)
					darray = list(all_data)

				elif result["type"] == "forward":
					tim = result["time"]
					mcollection = mdb['OUTPUT']
					qr = mcollection.find({"TD":{"$gte":datetime.datetime.strptime(tim, "%d-%m-%Y %H:%M:%S")}},{"_id":0}).sort([("TD",1)]).limit(1)
					qr = list(qr)
					if len(qr) > 0:
						qr = qr[0]
						all_data = mcollection.find({"SESSION":qr.get("SESSION"),"INID":qr.get("INID")},{"_id":0,"Authentication":0})
						darray.append(list(all_data))

				return jsonify(darray)
		except Exception as e:
				logger.exception("sqlget_output")
				return "None"


@app.route('/api',methods = ['POST', 'GET'])
def result():
	 dinput = 0
	 doutput = 0
	 draw = 0
	 if request.method == 'POST':
			result = request.form
			INID = int(result.get("INID"))
			SESSION = int(result.get("SESSION"))
			history = result.get("history")

			if history != None:
				h_time = result.get("time")
				mdb = mongoc.db
				mcollection = mdb['OUTPUT']

				if history == "back":
					#find({"$and":[{"TD":{"$lte":datetime.datetime.fromtimestamp(float(h_time))}}]},{"_id":0,"SESSION":1,"INID":1,"TD":1}).sort([("TD",-1)]).limit(1)
					qr = mcollection.find({ "$or" : [ { "INID" : {"$ne": int(INID)} }, { "SESSION" : {"$ne": int(SESSION)} } ] ,"TD":{"$lte":datetime.datetime.strptime(h_time+".999999", "%d-%m-%Y %H:%M:%S.%f")}}).sort([("TD",-1)]).limit(1)
					qr = list(qr)
					if len(qr) > 0:
						qr = qr[0]
						NEW_INID = int(qr.get("INID"))
						NEW_SESSION = int(qr.get("SESSION"))
						doutput = sqlget_output(NEW_SESSION,NEW_INID,LIVE=False)
					else:
						return "None"
				
				elif history == "forward":
					qr = mcollection.find({ "$or" : [ { "INID" : {"$ne": int(INID)} }, { "SESSION" : {"$ne": int(SESSION)} } ] ,"TD":{"$gte":datetime.datetime.strptime(h_time, "%d-%m-%Y %H:%M:%S")}}).sort([("TD",1)]).limit(1)
					qr = list(qr)
					if len(qr) > 0:
						qr = qr[0]
						NEW_INID = int(qr.get("INID"))
						NEW_SESSION = int(qr.get("SESSION"))
						doutput = sqlget_output(NEW_SESSION,NEW_INID,LIVE=False)
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
				NEW_INID = int(sesout.get("INID"))
				NEW_SESSION = int(sesout.get("SESSION"))

				if INID != int(NEW_INID) or SESSION != NEW_SESSION:
						# INPUT NEW UPDATE REQUIRED
						doutput = sqlget_output(NEW_SESSION,NEW_INID,LIVE=False)
				else:
						# Client side INPUT is uptodate ( Not required to update input data )
						doutput = 0
			
			return jsonify({"output": doutput,"INID":NEW_INID,"SESSION":NEW_SESSION})
			
	 if request.method == 'GET':
			return jsonify(sqlget_output("0"))

@app.route('/upload_input',methods = ['POST', 'GET'])
def upload_input():
	if request.method == 'POST':
		try:
			f = request.files['file']
			override = request.form.get('override')
			filename = secure_filename(f.filename)
			#jn = str(datetime.datetime.now().strftime("%d-%B-%H_%M_%S"))
			#filename = jn+"-"+filename
			check_file = os.path.join(app.config['UPLOAD_FOLDER'],filename)
			file_status = os.path.isfile(check_file)
			if file_status == True and override == "yes":
				f.save(check_file)
				return 'success'
			elif file_status == False:
				f.save(check_file)
				return 'success'
			else:
				return "File Exist"
		except Exception as e:
			logger.exception("upload_input")
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
			elif typ == "skip":
				mdb = mongoc.db
				mcollection = mdb['SESSION']
				mcollection.update({"_id":1},{ "$set": { "SKIP" : "yes"} })
				status = {"status": "Skipping" }
			return jsonify(status)
		except Exception as e:
			return jsonify({"status":"error"})

@app.route('/getgroup',methods = ['POST', 'GET'])
def get_group():
	try:
		status = {"status":"error"}
		if request.method == 'POST':
			fn = request.form.get('filename')
			if fn != None:
				filename = secure_filename(fn)
				full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
				data = get_xl_group(full_path)
				if data != None:
					return jsonify(data)
				else:
					return jsonify({"status":"error"})
		return jsonify(status)
	except Exception as e:
		logger.exception("get_group")
		return jsonify({"status":"error"})


@app.route('/new_job',methods = ['POST', 'GET'])
def new_job():
	global main_thread
	status = {"status":"error"}
	if request.method == 'POST':
		try:
			d_group = request.form.get('group')
			fn = request.form.get('filename')
			jn = request.form.get('jobname')
			apr = request.form.get('apprentice')
			try:
				apr = int(apr)
				if apr < 1:
					apr = 1
			except:
				apr = 1
			if fn == None or jn == None:
				return jsonify(status)
			jn = jn+"-"+str(datetime.datetime.now().strftime("%d-%B-%H:%M:%S"))
			filename = secure_filename(fn)
			if d_group != "no":
				#Create Tempravery file
				full_path2 = os.path.join(app.config['UPLOAD_FOLDER'], filename)
				new_xl_file = filename+"_temp_"+jn.replace(":","-")+"_"+str(random.randrange(10,10000))+".xlsx"
				new_xl_file = os.path.join(app.config['TEMP_FOLDER'], new_xl_file)
				grp = excell_filter(json.loads(d_group),full_path2,new_xl_file)
				full_path = new_xl_file
				if grp != True:
					return jsonify({"status":"error","type":"group error"})
			elif d_group == "no":
				full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
			if os.path.isfile(full_path):
				# Schudle Job
				if main_thread.isAlive() == False:
					main_thread = Thread(target=net_auto_modul.main_run,name = jn, args=(full_path,jn,apr,))
					main_thread.start()
					status = {"status":"Job Started"}
				else:
					status = {"status":"ExistingJobRunning"}
			else:
				status = {"status":"InputFileNotFound"}
			return jsonify(status)
		except Exception as e:
			logger.exception("new_job")
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
			logger.exception("delete_input")
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
			logger.exception("rawdownload")
			return "failed"


@app.route('/getsession',methods = ['POST', 'GET'])
def get_session():
	if request.method == 'POST':
		try:
			fn = request.form.get('session')
			if fn == "live":
				mdb = mongoc.db
				mcollection = mdb['SESSION']
				session = mcollection.find({"_id":1},{"_id":0})
				session = list(session)
				return jsonify({"session":session})
		except Exception as e:
			return "failed"



def get_xl_group(xl_file):
	try:
		xl = pandas.ExcelFile(xl_file)
		df1 = xl.parse('input')
		head = list(df1.columns.values)
		nd = []
		for index, row in df1.iterrows():
			gp = row.get("Group")
			le = row.get("Level")
			if gp != None and le != None:
				g = str(gp).split(",")
				l = str(le).split(",")
				d = {"Group":g,"Level":l}
				if d in nd:
					#No need to insert duplicate data
					pass
				else:
					nd.append(d)
		return {"data":nd}
	except Exception as e:
		logger.exception("get_xl_group")

def excell_filter(d_group,xl_file,new_xl_file):
	try:
		xl = pandas.ExcelFile(xl_file)
		df1 = xl.parse('input')
		head = list(df1.columns.values)
		head.remove("Group")
		head.remove("Level")
		nd = []
		for index, row in df1.iterrows():
			#row = list(row)
			g = str(row["Group"]).split(",")
			l = str(row["Level"]).split(",")
			row.pop("Group")
			row.pop("Level")
			for d in d_group:
				if d.get("Group") in g and d.get("Level") in l:
					if list(row) in nd:
						pass;
					else:
						nd.append(list(row))

		if len(nd) == 0:
			return False
		newdf = pandas.DataFrame(nd,columns=head)
		writer = pandas.ExcelWriter(new_xl_file)
		newdf.to_excel(writer, sheet_name='input',startrow=0,startcol=0,index = False)
		writer.save()
		return True
	except Exception as e:
		logger.exception("excell_filter")

if __name__ == '__main__':
	net_auto_modul = MonitorEngine.main_model()
	app.run(host="0.0.0.0", port=int("8888"), debug=True)