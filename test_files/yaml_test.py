
import yaml
import pymongo
import json
import sys
import os

mongoc = pymongo.MongoClient('/tmp/mongodb-27017.sock')
mdb = mongoc['LIVE']


def get_querys_from_yaml(self,credential_file,ip,function):
		try:
			fp = open(credential_file)
			jsn = yaml.load(fp)
			if jsn == None:
				logger.exception("get_querys_from_yaml > None JSON")
				return None
			all_list = []
			for data in jsn:
				if data.get("function") == function:
					# Function matched with YAML file
					host_list = data.get("host")
					if  host_list != None:
						host_list = host_list.split(" ")
						for host in host_list:
							if host == ip or host == "all":
								# Host Matched with YAML file
								for d in data.get("querys"):
									all_list.append(d)
								break;
			return all_list
		except Exception as e:
			logger.exception("get_querys_from_yaml")

def mongo_search_score(INID=92,session=1):
		try:
			logger.debug("Mongo search score for:"+str(str(INID)+" "+str(session)))
			mdb_out = mdb['OUTPUT']
			all_data = mdb_out.find({"INID":INID,"SESSION":session})
			for single_host in all_data:
				try:
					#print single_host
					IP = single_host.get("IP")
					logger.debug("mongo_search_score > Starting score for > "+str(IP))
					mon_objects = single_host.get("Objects")
					obj_index = -1
					for mon_obj in mon_objects:
						obj_index = obj_index + 1
						#ranks = mon_obj.get("rank")
						# Converting Test to JSON
						#ranks = json.loads(ranks)
						elmt_id = mon_obj.get("id")
						last_score = 100
						note = ""
						function = mon_obj.get("function")
						ranks = get_querys_from_yaml("","yam.yaml",IP,function)
						if type(ranks) != list:
							pass;
							logger.error("mongo_search_score > QUERY not found in YAML for:"+str(IP)+":"+str(function))
						for rank in ranks:
							#print rank
							#custom_query = json.loads(rank.get("Q"))
							custom_query = rank.get("Q")
							score = rank.get("score")
							dafault_query = {"INID":INID,"SESSION":session,"IP":IP}
							#print custom_query
							new_dict = {"out."+key: value for key, value in custom_query.items()}
							#print new_dict
							new_dict.update({"id":elmt_id})
							elmts = {"$elemMatch":new_dict}
							dafault_query.update({'Objects':elmts})
							logger.debug("mongo_search_score > searching DB for:"+str(dafault_query))
							queryout = mdb_out.find_one(dafault_query,{"_id":0,"TD":0})
							#print queryout
							if queryout == None:
								logger.debug("mongo_search_score > Pattern Not matched")
							else:
								# For adding issue note
								if score != 100:
									if type(rank.get("Q")) == dict:
										for k,v in rank.get("Q").iteritems():
											note = note + str(k) + ","

								logger.debug("mongo_search_score > Pattern Matched")
								# Update very lowest score in rank pattern
								if last_score >= score:
									last_score = score
									d = dafault_query,{"$set": {"Objects.$"+".score":last_score}}
									logger.debug("mongo_search_score > updating score >"+str(d))
									mdb_out.update(dafault_query,{"$set": {"Objects.$"+".score":last_score,"Objects.$"+".note":note}})
				except Exception as e:
					logger.exception("mongo_search_score")
		except Exception as e:
			logger.exception("mongo_search_score")


#print get_credentials_from_yaml("","yam.yaml","10.1.1.1","cisco_switch")
mongo_search_score()
