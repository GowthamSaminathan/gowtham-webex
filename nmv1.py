import logging
from logging.handlers import RotatingFileHandler
import re
from pexpect import pxssh
import pexpect
import easysnmp
import getpass
import os
import datetime
import dateparser

logger =  logging.getLogger("Rotating Log nmv1")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(os.getcwd()+"/nmv1.log",maxBytes=5000000,backupCount=25)
formatter = logging.Formatter('%(asctime)s > %(levelname)s > %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def system_uptime_snmp(ses,monobj):
	try:
		out = {"result":"failed"}
		ses = ses.get("snmp_session")
		uptime = ses.get('.1.3.6.1.2.1.1.3.0').value
		if uptime == "NOSUCHINSTANCE":
			out.update({"snmp":"no oid instance"})
			pass;
		else:
			if int(uptime) > 100:
				uptime = str(datetime.timedelta(seconds=int(uptime)/100))
				out.update({"result":"success","uptime":uptime})
			else:
				uptime = uptime
				out.update({"result":"success","uptime":uptime})
		return out
	except Exception as e:
		logger.exception("snmp_sys_uptime")
		return out	

def raw(ses,monobj):
	try:
		ses = ses.get("ssh_session")
		out = {"result":"failed"}
		mon = monobj.get("input")
		mon = mon.get("cmd").split(",")
		exp = mon.get("exp")
		if exp == None:
			exp = ses[1]
		#ses[0].sendline("terminal length 0")
		for cmd in mon:
			ses[0].sendline(cmd)
			ses[0].expect([cmd,pxssh.TIMEOUT])
			ses[0].expect([exp,pxssh.TIMEOUT],timeout=300)
			#data = str(ses[0].before)
		out.update({"result":"success"})
		return out
	except Exception as e:
		logger.exception("raw")
		return out

def ios_cpu(ses,monobj):
	try:
		ses = ses.get("ssh_session")
		out = {}
		exp = ses[1]
		cmd = "sh processes cpu sorted | i one minute:"
		#s[0].sendline("terminal length 0")
		ses[0].sendline(cmd)
		ses[0].expect([cmd,pxssh.TIMEOUT],timeout=5)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(s[0].before)
		b = data.split(";")[1].split(":")[1].strip()
		if b != None or len(str(b)) > 0:
		   out.update({"cpu:":int(b)})
		   return out
		else:
			 return out
	except Exception as e:
		logger.exception("cis_cpu_uti")
		return out

def nexus_cpu(ses,monobj):
	try:
		print "Starting 1"
		s = ses.get("ssh_session")
		exp = s[1]
		out = {}
		po=["CPU"]
		cmd = " sh system resources | i \"states\" "
		#s[0].sendline("terminal length 0")
		s[0].sendline(cmd)
		s[0].expect([cmd,pxssh.TIMEOUT],timeout=5)
		s[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(s[0].before)
		ot=""
		ot1=""
		pos = data.find("CPU")
		if pos > -1:
			print "Starting 2"
			n = filter(None,data[pos:].split("\n")[0].split(" "))
			ideal = round ( float (n[7].replace("%"," ")))
			ot = str(ideal)
			ot = ot.strip()
			free = 100 - ideal
			ot1 = str(free)
			ot1 = ot1.strip()
		#out.update({"Ideal":ot})
			out.update({"cpu":float(ot1)})
		print "CPU>",out
		return out
	except Exception as e:
		print "Err",e
		logger.exception("nexus_cpuutil")
		return out

def ios_memory(ses,monobj):
	try:
		out = {}
		s = ses.get("ssh_session")
		exp = s[1]
		cmd = " show processes memory | i Processor "
		#s[0].sendline("terminal length 0")
		s[0].sendline(cmd)
		s[0].expect([cmd,pxssh.TIMEOUT],timeout=5)
		s[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(s[0].before)
		ot=""
		ot1=""
		pos = data.find("Pool")
		if pos > -1:
			n = filter(None,data[pos:].split("\n")[0].split(" "))
			ot = n[4]
			ot = ot.strip()
			ot1 = n[6]
			ot1 = ot1.strip()
			out.update({"Used":float(ot)})
		#out.update({"Free":ot1})
		print out
		return out
	except Exception as e:
		print e
		logger.exception("mem_util")
		return out



def nexus_memory(ses,monobj):
	try:
		out = {}
		s = ses.get("ssh_session")
		exp = s[1]
		cmd = " sh system resources | i \"usage\" "
		#s[0].sendline("terminal length 0")
		s[0].sendline(cmd)
		s[0].expect([cmd,pxssh.TIMEOUT],timeout=5)
		s[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(s[0].before)
		ot=""
		ot1=""
		pos = data.find("Memory")
		if pos > -1:
			n = filter(None,data[pos:].split("\n")[0].split(" "))
			ot = n[4]
			ot = ot.strip()
			out.update({"memory":float(ot)})
		#out.update({"Free":ot1})
		#out.update({"Total":ot2})
		#print out
		print "MEM",out
		return out
	except Exception as e:
		print "Err",e
		logger.exception("nexus_memutil")
		return out


def juniper_interface(ses,monobj):
	# Monitor cisco switch interface : speed, duplex, error , bits 
	try:
		ses = ses.get("ssh_session")
		out = {}
		x_input = monobj.get("input")
		mon_ = x_input.get("check")
		mon_ = mon_.split(",")
		in_ = x_input.get("interface")

		exp = ses[1]
		cmd = "show interface "+in_+" | no-more"
		#ses[0].sendline("terminal length 0")
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		ses[0].sendline(cmd)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before).lower()
		
		if re.search(r'physical link is up',data):
			out.update({"interface":"up"})
		else:
			return {"interface":"down"}

		if "bits" in mon_:
			irate = ""
			orate = ""
			
			redata = re.search(r'input rate.*[0-9].*bps',data)

			if redata:
				irate = redata.group(0).split(":")[1].replace(" ","")

			redata = re.search(r'output rate.*[0-9].*bps',data)

			if redata:
				orate = redata.group(0).split(":")[1].replace(" ","")

			out.update({"inrate":irate,"outrate":orate})
		
		if "duplex" in mon_:
			if data.find("half") != -1:
				out.update({"duplex":"Half"})
			if data.find("full") != -1:
				out.update({"duplex":"Full"})

		if "speed" in mon_:
			speed = ""
			spd = re.search(r'speed:.*[0-9].*,',data)
			if spd:
				speed = spd.group(0).split(":")[1].replace(" ","").replace(",","")
			
			out.update({"speed":speed})


		if "error" in mon_:
			error = ""
			err = re.search(r'bpdu error: .*,',data)
			if err:
				error = err.group(0).split(",")[0].replace("bpdu error: ","")
				if error == "none":
					error = "0"
				out.update({"error":error})
		return out
	except Exception as e:
		logger.exception("juniper_interface")



def ios_interface(ses,monobj):
	# Monitor cisco switch interface : speed, duplex, error , bits 
	try:
		ses = ses.get("ssh_session")
		out = {}
		x_input = monobj.get("input")
		mon_ = x_input.get("check")
		mon_ = mon_.split(",")
		in_ = x_input.get("interface")

		exp = ses[1]
		cmd = "show interface "+in_
		#ses[0].sendline("terminal length 0")
		ses[0].sendline(cmd)
		ses[0].expect([cmd,pxssh.TIMEOUT],timeout=5)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before).lower()
		
		if data.find("line protocol is up") != -1 or data.find("admin state is up") != -1:
			out.update({"interface":"up"})
		else:
			return {"interface":"down"}

		if "bits" in mon_:
			irate = ""
			orate = ""
			
			redata = re.findall(r'input rate [0-9]+',data)

			if len(redata) > 0:
				irate = redata[0].replace('input rate ','')

			redata = re.findall(r'output rate [0-9]+',data)
			
			if len(redata) > 0:
				orate = redata[0].replace('output rate ','')
				#rate = irate+"|"+orate
			out.update({"inrate":irate,"outrate":orate})
		
		if "duplex" in mon_:
			if data.find("half") != -1:
				out.update({"duplex":"Half"})
			if data.find("full") != -1:
				out.update({"duplex":"Full"})

		if "speed" in mon_:
			redata = re.findall(r'[0-9]+.mb/s,',data)
			
			# For IOS switch interfaces
			if len(redata) == 0:
				redata = re.findall(r'[0-9]+.mbps,',data)
			
			if len(redata) > 0:
				redata = redata[0].strip()
				redata = redata.replace(",","")
				out.update({"speed":redata})
			
			# For Nexus switch interface
			redata = re.findall(r'[0-9]+.gb/s',data)
			if len(redata) > 0:
				redata = redata[0].split("gb")[0]
				redata = redata.strip()
				redata = redata+"000"+"mb/s"
				out.update({"speed":redata})


		if "error" in mon_:
			redata = re.findall(r'total output drops: [0-9]+',data)
			if len(redata) == 1:
				outdrop = redata[0].replace('total output drops: ','')
				out.update({"outdrops":outdrop})

			redata = re.findall(r'[0-9]+ input error',data)
			if len(redata) == 1:
				inerror = redata[0].replace(' input error','')
				out.update({"inerror":inerror})

			redata = re.findall(r'[0-9]+ crc',data)
			if len(redata) == 1:
				crcerror = redata[0].replace(' crc','')
				out.update({"crc":crcerror})
		return out
	except Exception as e:
		logger.exception("cis_sw_int")

def nexus_interface(ses,monobj):
	# Monitor cisco switch interface : speed, duplex, error , bits 
	try:
		ses = ses.get("ssh_session")
		out = {}
		x_input = monobj.get("input")
		mon_ = x_input.get("check")
		mon_ = mon_.split(",")
		in_ = x_input.get("interface")

		exp = ses[1]
		cmd = "show interface "+in_
		#ses[0].sendline("terminal length 0")
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		ses[0].sendline(cmd)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before).lower()
		
		
		if re.search(r'[0-9]+ is up',data):
			out.update({"interface":"up"})
		else:
			return {"interface":"down"}

		if "bits" in mon_:
			irate = ""
			orate = ""
			
			redata = re.findall(r'seconds input rate [0-9]+',data)

			if len(redata) > 0:
				irate = redata[0].replace('seconds input rate ','')

			redata = re.findall(r'seconds output rate [0-9]+',data)
			
			if len(redata) > 0:
				orate = redata[0].replace('seconds output rate ','')
				#rate = irate+"|"+orate
			out.update({"inrate":irate,"outrate":orate})
		
		if "duplex" in mon_:
			if data.find("half") != -1:
				out.update({"duplex":"Half"})
			if data.find("full") != -1:
				out.update({"duplex":"Full"})

		if "speed" in mon_:
			speed = ""
			spd = re.search(r'duplex, [0-9]+.mb/s',data)
			if spd:
				spd = spd.group(0).replace("duplex, ","")
				spd = spd.replace(" mb/s","")
				speed = spd+"mb/s"
			else:
				spd = re.search(r'duplex, [0-9]+.gb/s',data)
				if spd:
					spd = spd.group(0).replace("duplex, ","")
					spd = spd.replace(" gb/s","")
					speed = spd+"000"+"mb/s"
			out.update({"speed":speed})


		if "error" in mon_:
			
			redata = re.findall(r'[0-9]+ output error',data)
			if len(redata) == 1:
				outerror = redata[0].replace(' output error','')
				out.update({"outdrops":outerror})

			redata = re.findall(r'[0-9]+ input error',data)
			if len(redata) == 1:
				inerror = redata[0].replace(' input error','')
				out.update({"inerror":inerror})

			redata = re.findall(r'[0-9]+ crc',data)
			if len(redata) == 1:
				crcerror = redata[0].replace(' crc','')
				out.update({"crc":crcerror})
		return out
	except Exception as e:
		logger.exception("nexus_sw_int")


def juniper_stp(ses,monobj):
	try:
		ses = ses.get("ssh_session")
		out = {}
		
		#x_input = monobj.get("input")
		#mon_ = x_input.get("check")
		#mon_ = mon_.split(",")
		#in_ = x_input.get("interface")
		
		exp = ses[1]
		cmd = "show spanning-tree bridge | no-more"
		#ses[0].sendline("terminal length 0")
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		ses[0].sendline(cmd)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before).lower()
		print data
		s = re.search(r'last topology change.*[0-9].*seconds',data)
		if s != None:
			x = s.group()
			d = int(x.split('last topology change   : ')[1].split(" seconds")[0].strip())
			# topology change in seconds
			out.update({"topology change":int(d)})
		return out
	except Exception as e:
		logger.exception("juniper_stp")
		return out

def cisco_stp(ses,monobj):
	try:
		ses = ses.get("ssh_session")
		out = {}
		
		#x_input = monobj.get("input")
		#mon_ = x_input.get("check")
		#mon_ = mon_.split(",")
		#in_ = x_input.get("interface")

		exp = ses[1]
		cmd = "show spanning-tree detail | i last change occurred"
		#ses[0].sendline("terminal length 0")
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		ses[0].sendline(cmd)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before).lower()
		s = re.findall(r'last change occurred.*ago',data)
		last_change = []
		if type(s) == list:
			for x in s:
				dtime = x.replace('last change occurred ',"").replace(" ago","").strip()
				if dtime.find(":") != -1:
					# Converting H:M:S to seconds
					h,m,s = re.split(':',dtime)
					time_in_sec = int(datetime.timedelta(hours=int(h),minutes=int(m),seconds=int(s)))
					time_in_sec = time_in_sec.total_seconds()
					last_change.append(time_in_sec)
				else:
					dtime = dtime.replace("y",'years')
					dtime = dtime.replace("h",'hours')
					dtime = dtime.replace("w",'weeks')
					dtime = dtime.replace("d",'days')
					dtime = dtime.replace("m",'months')
					time_in_sec = datetime.datetime.now() - dateparser.parse(dtime)
					time_in_sec = time_in_sec.total_seconds()
					last_change.append(time_in_sec)

			# Get Minimum value from list to get very latest change
			if len(last_change) > 0:
				last_change = last_change[last_change.index(min(last_change))]
				out.update({"topology change":last_change})
		return out
	except Exception as e:
		logger.exception("cisco_stp")
		return out


def juniper_memory(ses,monobj):
	try:
		ses = ses.get("ssh_session")
		out = {"memory":[]}
		#x_input = monobj.get("input")
		#mon_ = x_input.get("check")
		#mon_ = mon_.split(",")
		#in_ = x_input.get("interface")

		exp = ses[1]
		cmd = "show chassis routing-engine | no-more"
		#ses[0].sendline("terminal length 0")
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		ses[0].sendline(cmd)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before).lower()
		s = re.findall(r'Memory utilization.*[0-9] percent',data)
		all_mem = []
		
		if type(s) == list:
			for indx , x in enumerate(s):
				d = int(x.split('memory utilization')[1].split("percent")[0].strip())
				all_mem.append(d)
				out.update({"memory":all_mem})
		return out
	except Exception as e:
		logger.exception("juniper_memory")
		return out

def juniper_cpu(ses,monobj):
	try:
		ses = ses.get("ssh_session")
		out = {"cpu":[]}
		#x_input = monobj.get("input")
		#mon_ = x_input.get("check")
		#mon_ = mon_.split(",")
		#in_ = x_input.get("interface")

		exp = ses[1]
		cmd = "show chassis routing-engine | no-more"
		#ses[0].sendline("terminal length 0")
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		ses[0].sendline(cmd)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before).lower()
		s = re.findall(r'Idle.*[0-9] percent',data)
		all_mem = []
		
		if type(s) == list:
			for indx , x in enumerate(s):
				d = 100 - int(x.split('idle')[1].split("percent")[0].strip())
				all_mem.append(d)
				out.update({"cpu":all_mem})
		return out
	except Exception as e:
		logger.exception("juniper_cpu")
		return out


def cisco_bgp(ses,monobj):
	try:
		ses = ses.get("ssh_session")
		out = {}
		mon_ = monobj.get("monitor")
		mon_ = mon_.split(",")
		
		type_ = monobj.get("type")
		in_ = monobj.get("name")

		exp = ses[1]
		cmd = "show ip bgp summary "
		ses[0].sendline("terminal length 0")
		ses[0].sendline(cmd)
		ses[0].expect([cmd,pxssh.TIMEOUT],timeout=5)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before)
		all_ot = []
		for host in mon_:
			try:
				ot=""
				pos = data.find(host)
				if pos > -1:
					n = filter(None,data[pos:].split("\n")[0].split(" "))
					ot = {"neighbor":n[0].strip(),"AS":n[2].strip(),"uptime":n[-2].strip(),"received-prf":n[-1].strip()}
					all_ot.append(ot)
			except Exception as e:
				logger.exception("cis_bgp Ex1")
			out.update({"BGP":all_ot})
		return out
	except Exception as e:
		logger.exception("cis_bgp Ex2")

def juniper_bgp(ses,monobj):
	try:
		ses = ses.get("ssh_session")
		out = {}
		
		#x_input = monobj.get("input")
		#mon_ = x_input.get("check")
		#mon_ = mon_.split(",")
		#in_ = x_input.get("interface")

		exp = ses[1]
		cmd = 'show bgp summary | display xml | match "peer-address|stat|received-prefix-count|junos:seconds" | no-more'
		#ses[0].sendline("terminal length 0")
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		ses[0].sendline(cmd)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before).lower()
		all_peers = []
		all_state = []
		all_time = []
		s = re.findall(r'peer-address>.*<',data)
		for x in s:
			all_peers.append(x.replace("peer-address>","").replace("<","").strip())
		s = re.findall(r'junos:format=.*|junos:format|peer-state>.*',data)
		for t in s:
			all_state.append(t.split(">")[1].split("<")[0].strip())
		s = re.findall(r'junos:seconds=.*',data)
		for x in s:
			all_time.append(x.split("=")[1].split(">")[0].replace('"',"").strip())
		
		all_out = []
		for l in xrange(len(all_peers)):
			all_out.append({"peer":all_peers[l],"state":all_state[l],"time":all_time[l]})
		out = {"BGP":all_out}
		return out
	except Exception as e:
		logger.exception("juniper_stp")
		return out

def fortigate_interface(ses,monobj):
	try:
		ses = ses.get("ssh_session")
		out = {}
		all_out = {}
		
		x_input = monobj.get("input")
		mon_ = x_input.get("interface")
		#mon_ = mon_.split(",")
		#in_ = x_input.get("interface")

		exp = ses[1]
		cmd = 'get system interface physical'
		#ses[0].sendline("terminal length 0")
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		ses[0].sendline(cmd)
		ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
		data = str(ses[0].before).lower()
		for one_int in mon_.split(","):
			out = {}
			out.update({"interface":one_int})
			s = re.search(one_int+'.*?==',data,re.S)
			if s!= None:
				s = s.group(0)
				int_status = re.search(r'status.*',s).group().replace("status:","").strip()
				out.update({"status":int_status})
				spd_dup = re.search(r'speed:.*',s).group()
				s = re.search(r'speed:.*',s).group()
				if s!= None:
					s = s.split("(")
					if len(s) == 2:
						speed = s[0].replace("speed:","").strip()
						duplex = s[0].replace("Duplex:","").replace(")","").strip()
						out.update({"speed":speed,"duplex":duplex})
			if len(out) != 0:
				all_out.append(out)
		
		return {"fortigate_interface":all_out}
	except Exception as e:
		logger.exception("fortigate_interface")
		return all_out

if __name__ == "__main__":
	pass;
