import pymongo

a = {'SESSION': 1}

def mongo_search():
    mongoc = pymongo.MongoClient('127.0.0.1', 27017)
    mdb = mongoc['LIVE']
    mdb_out = mdb['SESSION']
    all_data = mdb_out.find_one(a)
    print all_data.get("JOBNAME")


mongo_search()
