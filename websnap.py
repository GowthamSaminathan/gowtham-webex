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
					qr = mcollection.find({ "$or" : [ { "INID" : {"$ne": int(iin_update)} }, { "SESSION" : {"$ne": int(oout_update)} } ] ,"TD":{"$lte":datetime.datetime.strptime(h_time, "%d-%m-%Y %H:%M:%S")}}).sort([("TD",-1)]).limit(1)
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
					qr = mcollection.find({ "$or" : [ { "INID" : {"$ne": int(iin_update)} }, { "SESSION" : {"$ne": int(oout_update)} } ] ,"TD":{"$gte":datetime.datetime.strptime(h_time, "%d-%m-%Y %H:%M:%S")}}).sort([("TD",1)]).limit(1)
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
		print request.form
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
        	print "upload_input Error>"+str(e)
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
		print "Get Group Error>"+str(e)
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
			print "new_job>"+str(e)
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
    	print "get_xl_group Error>"+str(e)

def excell_filter(d_group,xl_file,new_xl_file):
    try:
        xl = pandas.ExcelFile(xl_file)
        df1 = xl.parse('input')
        head = list(df1.columns.values)
        head.remove("Group")
        head.remove("Level")
        nd = []
        print d_group
        for index, row in df1.iterrows():
        	#row = list(row)
        	g = str(row["Group"]).split(",")
        	l = str(row["Level"]).split(",")
        	row.pop("Group")
        	row.pop("Level")
        	for d in d_group:
        		print ">>"
        		if d.get("Group") in g and d.get("Level") in l:
        			print "1>>"
        			print index,row["IP"]
        			print row
        			if list(row) in nd:
        				pass;
        			else:
        				nd.append(list(row))
        				print "2>>"
        	print "3>>"
        if len(nd) == 0:
        	return False
        print nd
        print new_xl_file
        newdf = pandas.DataFrame(nd,columns=head)
        writer = pandas.ExcelWriter(new_xl_file)
        newdf.to_excel(writer, sheet_name='input',startrow=0,startcol=0,index = False)
        writer.save()
        return True
    except Exception as e:
        print ("Excell Filter Error >",e)

if __name__ == '__main__':
	net_auto_modul = MonitorEngine.main_model()
	app.run(host="0.0.0.0", port=int("8888"), debug=True)
