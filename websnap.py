from flask import Flask, render_template, request , send_file
from flask import jsonify
from werkzeug.utils import secure_filename
import json
import yaml
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

logger.info("Starting Websnap")


app = Flask(__name__,static_url_path='/static')
app.config['MONGO_DBNAME'] = 'LIVE'
app.config['MONGO_URI'] = 'mongodb://127.0.0.1:27017/LIVE'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(),"input_file")
app.config['TEMP_FOLDER'] = os.path.join(os.getcwd(),"temp_file")
mongoc = PyMongo(app)


									 
def sqlget_input(INID):
	try:
		# connect to LIVE database
		mdb = mongoc.db
		mcollection = mdb['INPUT']
		all_data = mcollection.find({"INID":INID},{"_id":0})
		return list(all_data)
	except Exception as e:
		logger.exception("sqlget_input")

def sqlget_output(INID):
	try:
		mdb = mongoc.db
		mcollection = mdb['OUTPUT']
		all_data = mcollection.find({"INID":INID},{"_id":0})
		return list(all_data)
	except Exception as e:
		logger.exception("sqlget_output")


@app.route('/')
def main():
	 return render_template('index.html')

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


@app.route('/api/v1/skip_job',methods = ['POST', 'GET'])
def skip_job():
	"""
	Skip the running job by INID
	update 'skip' to 'yes' in 'SESSION' table  

	"""
	status = {"status":"error"}
	if request.method == 'POST':
		try:
			print request.form
			typ = request.form.get('type')
			INID = request.form.get('INID')
			if typ == "skip":
				mdb = mongoc.db
				mcollection = mdb['HISTORY']
				mcollection.update({"INID":int(INID)},{ "$set": { "SKIP" : "yes"} })
				status = {"status": "Skipping" }
			return jsonify(status)
		except Exception as e:
			return jsonify({"status":"error"})


@app.route('/api/v1/new_job',methods = ['POST', 'GET'])
def new_job():
	"""

	"""
	status = {"status":"error"}
	if request.method == 'POST':
		try:
			d_group = request.form.get('group')
			fn = request.form.get('filename')
			jn = request.form.get('jobname')
			apr = request.form.get('apprentice')
			
			if apr > 0:
				if fn == None or jn == None:
					return jsonify(status)
				filename = secure_filename(fn)
				full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
				INID = None
				
				try:
					mdb = mongoc.db
					mcollection = mdb['SESSION']
					new_id = mcollection.find_and_modify(query = {"_id":1}, update = { "$inc": { "INID" : 1 }})
					# Need to increase to sync with database INID
					INID = new_id.get("INID")
					INID = INID + 1
				except Exception as e:
					logger.exception("new_job INID")
				
				if INID == None:
					return jsonify({"status":"error","type":"Creating INID failed"})
				if os.path.isfile(full_path):
					main_thread = Thread(target=net_auto_modul.main_run,name = jn, args=(full_path,jn,apr,INID,))
					main_thread.start()
					status = {"status":"Job Started","INID":INID}
				else:
					status = {"status":"InputFileNotFound"}
				return jsonify(status)
			else:
				return jsonify({"status":"error","type":"apprentice not valid"})
		except Exception as e:
			logger.exception("new_job")
			return jsonify({"status":"error"})

@app.route('/api/v1/getby',methods = ['POST', 'GET'])
def get_by():
	"""
	Get output by its INID with HISTORY status
	"""
	if request.method == 'POST' or "GET":
		try:
			INID = int(request.form.get('INID'))
			mdb = mongoc.db
			mcollection = mdb['HISTORY']
			session = mcollection.find_one({"INID":INID},{"_id":0,"STATUS":0})
			if session != None:
				INID = session.get("INID")
				out = sqlget_output(INID)
				if type(out) == list:
					sts = {"completed":"yes","jobs":session,"output":out}
					return jsonify(sts)
				else:
					return jsonify({"completed":"no"})
			else:
				return jsonify({"completed":"no"})
		except Exception as e:
			print e
			return jsonify({"error":"getcompleted"})


@app.route('/api/v1/getcompleted',methods = ['POST', 'GET'])
def get_completed():
	
	"""
	Get completed jobs detail from 'SESSION' table
	return 'INID,JOBNAME,STARTED DATE,JOBSTATUS' if job is in completed state and matches history

	"""
	if request.method == 'POST' or "GET":
		try:
			history = request.form.get('history')
			dat_tim = request.form.get('time')
			limit = request.form.get('limit')
			outputrequired = request.form.get('outputrequired')
			if limit != None:
				limit = int(limit)
			else:
				limit = 1
			if dat_tim != None:

				if history == "back":
					if outputrequired != "yes":
						top_history_required = ".9999"
					else:
						top_history_required = ".0000"
					search = {"startedtime":{"$lte":datetime.datetime.strptime(dat_tim+top_history_required, "%d-%m-%Y %H:%M:%S.%f")}}
					short = -1
				elif history == "forward":
					search = {"startedtime":{"$gte":datetime.datetime.strptime(dat_tim+".9999", "%d-%m-%Y %H:%M:%S.%f")}}
					short = 1
				else:
					return jsonify({"completed":"no" , "error":"not valid input"})
				
				mdb = mongoc.db
				mcollection = mdb['HISTORY']
				search.update({"JOBSTATUS":"completed"})

				if outputrequired == "yes":
					session = mcollection.find(search,{"_id":0,"STATUS":0}).sort([("startedtime",short)]).limit(1)
					session = list(session)
					if len(session) > 0:
						session = session [0]
				else:
					session = mcollection.find(search,{"_id":0,"STATUS":0}).sort([("startedtime",short)]).limit(limit)
					session = list(session)
				
				if len(session) > 0:
					# Found completed jobs
					sts =  {"completed":"yes","jobs":session}
					if outputrequired == "yes":
						# Get output for INID
						out = sqlget_output(session.get("INID"))
						if type(out) == list:
							sts.update({"output":out})
					return jsonify(sts)
				else:
					# No completed jobs found
					return jsonify({"completed":"no"})
			else:
				return jsonify({"error":"getcompleted"})
		except Exception as e:
			return jsonify({"error":"getcompleted"})


@app.route('/api/v1/getrunning',methods = ['POST', 'GET'])
def get_running():
	"""
	Get all running jobs detail from 'SESSION' table
	return 'INID,JOBNAME,STARTED DATE,JOBSTATUS' if job is in running state
	
	"""
	if request.method == 'POST' or "GET":
		try:
			#fn = request.form.get('session')
			mdb = mongoc.db
			mcollection = mdb['HISTORY']
			session = mcollection.find({"JOBSTATUS":"running"},{"_id":0,"STATUS":0})
			session = list(session)
			if len(session) > 0:
				# Found running jobs
				return jsonify({"running":"yes","jobs":session})
			else:
				# No running jobs found
				return jsonify({"running":"no"})
		except Exception as e:
			print e
			return jsonify({"error":"getrunning"})

@app.route('/api/v1/getstatus',methods = ['POST', 'GET'])
def get_status():
	"""
	Get status of the job by INID from 'SESSION' table
	return 'INID,JOBNAME,STARTED DATE,JOBSTATUS' if 'outputrequired' is true 
	then search 'OUTPUT' table for INID and retun the result
	
	"""
	if request.method == 'POST' or "GET":
		try:
			
			INID = int(request.form.get('INID'))
			outputrequired = request.form.get('outputrequired')
			mdb = mongoc.db
			
			mcollection = mdb['HISTORY']
			session = mcollection.find_one({"INID":INID},{"_id":0})
			
			if session != None:
				# Found running jobs
				sts = {"status":"yes","jobs":session}
				if outputrequired == "yes":
					# Get output for INID
					out = sqlget_output(INID)
					if type(out) == list:
						sts.update({"output":out})
				return jsonify(sts)
			else:
				# No running jobs found
				return jsonify({"status":"no"})
		except Exception as e:
			return jsonify({"error":"getstatus"})

@app.route('/api/v1/getlast',methods = ['POST', 'GET'])
def get_last():

	"""
	Get last completed job from 'SESSION' table
	return 'INID,JOBNAME,STARTED DATE,JOBSTATUS' if 'outputrequired' is true 
	then search 'OUTPUT' table for INID and retun the result
	
	"""
	if request.method == 'POST' or "GET":
		try:
			outputrequired = request.form.get('outputrequired')
			know_id = request.form.get('knowninid')
			if know_id != None:
				know_id = int(know_id)
			
			mdb = mongoc.db
			mcollection = mdb['SESSION']
			last_completed = mcollection.find_one({"_id":1},{"_id":0})
			
			if last_completed != None:
				INID = last_completed.get("LASTINID")
			else:
				return jsonify({"completed":"no"})

			# knownid send by client if knownid and LASTINID is same then no need to send same output to user
			if INID == None or know_id == INID:
				return jsonify({"completed":"no"})

			mcollection = mdb['HISTORY']
			session = mcollection.find_one({"INID":INID},{"_id":0})
			
			if session != None:
				# Found completed job
				sts = {"completed":"yes","jobs":session}
				if outputrequired == "yes":
					# Get output for completed job
					out = sqlget_output(INID)
					if type(out) == list:
						sts.update({"output":out})
				return jsonify(sts)
			else:
				# No running jobs found
				return jsonify({"completed":"no"})
		except Exception as e:
			return jsonify({"error":"getstatus"})


@app.route('/merge_js_yaml',methods = ['POST', 'GET'])
def merge_js_yaml():
	if request.method == 'POST':
		try:
			js_data = request.form.get('js')
			yaml_data = request.form.get('yaml')
			if js_data == None:
				logger.info("merge_js_yaml > no csv data found")
				return "no csv data found"
			else:
				js_data = json.loads(js_data)
				# Merging json and yaml
				yaml_js = yaml.load(yaml_data)
				netsnap = yaml_js.get("networksnap")
				if netsnap == None or type(netsnap) != list:
					netsnap = []
					new_entry = True
					#return jsonify({"error":"Not valid job file => networksnap not found"})

				for js in js_data:
					js_ip = js.get("IP")
					js_host = str(js.get("Hostname"))
					js_fun = js.get("function")
					js_inp = js.get("input")
					if js_ip == None or js_ip == "" or js_fun == None or js_inp == None:
						logger.info("merge_js_yaml > Some data missed in JS , skipping")
						continue;
					for ns in netsnap:
						objects = ns.get("Objects")
						host_ip = ns.get("IP")
						new_entry = True
						if objects == None or host_ip == None:
							return jsonify({"error":"object not found for IP "+str(host_ip)})
						if host_ip == js_ip:
							new_entry = False
							# host already exist need to merge functions
							fun = js.get("function")
							inp = js.get("input")
							objects.append({"function":fun,"input":json.loads(inp)})
							ns.update({"Objects":objects})
							break;
					if new_entry == True:
						# no existing host found need add new host
						new_obj = {"Objects":[{"function":js_fun,"input":json.loads(js_inp)}],"IP":js_ip,"Hostname":js_host}
						netsnap.append(new_obj)


				yaml_js.update({"networksnap":netsnap})
				yaml_js =  yaml.safe_dump(yaml_js)
				return jsonify({"data":yaml_js})

		except Exception as e:
			logger.exception("merge_js_yaml")
			return "failed"


if __name__ == '__main__':
	net_auto_modul = MonitorEngine.main_model()
	app.run(host="0.0.0.0", port=int("8888"), debug=True)