import pymongo


def mongo_search():
    mongoc = pymongo.MongoClient('localhost', 27017)
    mdb = mongoc['LIVE']
    mdb_out = mdb['OUTPUT']
    all_data = mdb_out.find({"INID":1,"SESSION":1,"Objects.id":{"$lte":1},"Objects.out.status": "reachable"})
    for t in all_data:
        print t


mongo_search()
