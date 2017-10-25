
import yaml
import pymongo
import json
import sys
import os

def jsonify(p):
	print str(p)

js_data =  [ {"IP": "10.1.1.2", "function": "sexyyy", "input":"SEXXX"},{"IP": "10.1.1.2", "function": "ooo", "input":{"a":"a","b":"b"}},{"Hostname": "Host1", "IP": "10.1.1.1", "function": "Roudy", "input": "AAAAAAAAAAAAAAAA"},{"Hostname": "Host1", "IP": "10.1.1.1", "function": "Boy", "input": "Bbbbbbbbbbbb"} ]

yaml_data = """---
credential: default_auth
score: default_score
networksnap:
- Hostname: CHN_1
  IP: 10.1.1.1
  Objects:
  - function: self_check
    input:
      timeout: 10
      type: cisco
      check:
      - snmp
      - ssh
"""



def merge_js_yaml():
	if True == True:
		try:
			#js_data = request.form.get('js')
			#yaml_data = request.form.get('yaml')
			if js_data == None:
				# Compile only
				pass;
			else:
				# Merging json and yaml
				yaml_js = yaml.load(yaml_data)
				netsnap = yaml_js.get("networksnap")
				if netsnap == None or type(netsnap) != list:
					return jsonify({"error":"Not valid job file => networksnap not found"})

				for js in js_data:
					js_ip = js.get("IP")
					js_host = str(js.get("Hostname"))
					js_fun = js.get("function")
					js_inp = js.get("input")
					if js_ip == None or js_fun == None or js_inp == None:
						print "Some data missed in JS , skipping"
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
							objects.append({"function":fun,"input":inp})
							ns.update({"Objects":objects})
							break;
					if new_entry == True:
						# no existing host found need add new host
						new_obj = {"Objects":[{"function":js_fun,"input":js_inp}],"IP":js_ip,"Hostname":js_host}
						netsnap.append(new_obj)

				yaml_js.update({"networksnap":netsnap})
				return yaml.dump(yaml_js)
		except Exception as e:
			print e
			return "failed"



print merge_js_yaml()