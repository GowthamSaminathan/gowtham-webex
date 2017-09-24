import pymongo


def mongo_search():
    mongoc = pymongo.MongoClient('192.168.234.130', 27017)
    mdb = mongoc['LIVE']
    mdb_out = mdb['SESSION']
    all_data = mdb_out.find_one({"_id":1,"KILL":"yes"},{"KILL":1})
    print all_data


mongo_search()
