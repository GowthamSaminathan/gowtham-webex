import logging
from logging.handlers import RotatingFileHandler
import re
from pexpect import pxssh
import pexpect
import easysnmp
import getpass
import os
import datetime

logger =  logging.getLogger("Rotating Log nmv1")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(os.getcwd()+"/nmv1.log",maxBytes=5000000,backupCount=25)
formatter = logging.Formatter('%(asctime)s > %(levelname)s > %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def snmp_sys_uptime(ses,monobj):
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
		print e
		logger.exception("snmp_sys_uptime")
		return out	

def cis_raw(ses,monobj):
    try:
    	ses = ses.get("ssh_session")
        out = {"result":"failed"}
        mon = monobj.get("input")
        mon = mon.get("cmd").split(",")

        exp = ses[1]
        ses[0].sendline("terminal length 0")
        for cmd in mon:
            ses[0].sendline(cmd)
            ses[0].expect([cmd,pxssh.TIMEOUT])
            ses[0].expect([exp,pxssh.TIMEOUT],timeout=300)
            #data = str(ses[0].before)
        out.update({"result":"success"})
        return out
    except Exception as e:
    	logger.exception("cis_raw")
        return out

def cis_cpu_uti(ses,monobj):
    try:
    	ses = ses.get("ssh_session")
        out = {}
        exp = s[1]
        cmd = "sh processes cpu sorted | i one minute:"
        #s[0].sendline("terminal length 0")
        ses[0].sendline(cmd)
        ses[0].expect([cmd,pxssh.TIMEOUT],timeout=5)
        ses[0].expect([exp,pxssh.TIMEOUT],timeout=5)
        data = str(s[0].before)
        b = data.split(";")[1].split(":")[1].strip()
        if b != None or len(str(b)) > 0:
           out.update({"CPU_One minute:":b})
           return out
        else:
             return {"CPU_One minute:":""}
    except Exception as e:
    	logger.exception("cpu_uti")


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



def cis_sw_int(ses,monobj):
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

def nexus_sw_int(ses,monobj):
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


def cis_bgp(ses,monobj):
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


if __name__ == "__main__":
	pass;
