import yaml


def get_credentials_from_yaml(self,credential_file):
		try:
			fp = open(credential_file)
			jsn = yaml.load(fp)
			error = []
			all_ip = {}
			for j in jsn:
				gips = j.get("ip")
				if gips != None:
					gips = gips.split(" ")
					for gip in gips:
						check_dup_dic = dict(j)
						new_dic = dict(j)
						new_dic.pop("ip")
						all_ip.update({gip:new_dic})
				else:
					logger.warning("get_credentials_from_yaml : ip not found for: "+str(j))
			
			return all_ip
		except Exception as e:
			logger.exception("get_credentials")


print get_credentials_from_yaml("","yam.yaml")
