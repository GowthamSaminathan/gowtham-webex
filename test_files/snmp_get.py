from easysnmp import Session

b = {"hostname":"192.168.235.27","auth_password" : "npcictsnms","security_username":"NPCI_CTS_NMSV3","security_level":"auth_without_privacy","version":3}
session = Session(**b)

#NPCI_CTS_NMSV3
#str(datetime.timedelta(seconds=721979033/100))
#NOSUCHINSTANCE
print session.get('.1.3.6.1.2.1.1.3.0').value