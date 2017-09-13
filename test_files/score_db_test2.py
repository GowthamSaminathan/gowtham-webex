import pymongo


def mongo_search():
    mongoc = pymongo.MongoClient('localhost', 27017)
    mdb = mongoc['LIVE']
    mdb_out = mdb['OUTPUT']
    all_data = mdb_out.find({"INID":INID,"SESSION":session})
    for t in all_data:
        print t

def mongo_search_score(INID=47,session=1):
        try:
            mongoc = pymongo.MongoClient('localhost', 27017)
            mdb = mongoc['LIVE']
            mdb_out = mdb['OUTPUT']
            all_data = mdb_out.find({"INID":INID,"SESSION":session})
            for single_host in all_data:
                try:
                    #print single_host
                    mon_objects = single_host.get("Objects")
                    obj_index = -1
                    for mon_obj in mon_objects:
                        obj_index = obj_index + 1
                        ranks = mon_obj.get("rank")
                        elmt_id = mon_obj.get("id")
                        last_score = 0
                        for rank in ranks:
                            #print rank
                            custom_query = rank.get("regex")
                            score = rank.get("score")
                            dafault_query = {"INID":INID,"SESSION":session,"Objects.id":elmt_id}
                            #print custom_query
                            new_dict = {"Objects"+".out."+key: value for key, value in custom_query.items()}
                            #print new_dict
                            dafault_query.update(new_dict)
                            print dafault_query
                            queryout = mdb_out.find_one(dafault_query,{"_id":0,"TD":0})
                            #print queryout
                            if queryout == None:
                                print "Issue Pattern Not matched"
                            else:
                                print "Issue Pattern  Matched"
                                # Update very lowest score in rank pattern
                                if last_score < score:
                                    last_score = score
                                #tmpdesc = hostname+" "+ip+" "+str(emon)+" "+str(etype)+" "+str(ename)+" "+str(custom_query)+" "+str(last_score)+" "+str(queryout.get("OUT"))
                                #desc = desc+"\n"+str(tmpdesc)
                                #print "Issue pattern matched > ",desc
                                print dafault_query
                                mdb_out.update(dafault_query,{"$set": {"Objects.$"+".score":last_score}})
                except Exception as e:
                    print("mongo_search_score Error Position1:>"+str(e))
        except Exception as e:
            print("mongo_search_score Error Position0:>"+str(e))

def mongo_search_score33(INID=41,session=1):
    try:
        mongoc = pymongo.MongoClient('localhost', 27017)
        mdb = mongoc['LIVE']
        mcollection = mdb['INPUT']
        all_data = mcollection.find({"INID":INID})
        mdb_out = mdb['OUTPUT']
        for single_input in all_data:
            try:
                elements_input = single_input.get("Monitoring_obj")
                hostname = single_input.get("Hostname")
                ip = single_input.get("IP")
                input_id = single_input.get("ID")
                # Read elements for single hosts
                for elmt in elements_input:
                    try:
                        elmt_id = elmt.get("id")
                        emon = elmt.get("monitor")
                        etype = elmt.get("type")
                        ename = elmt.get("name")
                        elmt_rank = elmt.get("rank")
                        #print elmt
                        last_score = 100
                        desc = ""
                        for rank in elmt_rank:
                            custom_query = rank.get("regex")
                            score = rank.get("score")
                            dafault_query = {"INID":INID,"SESSION":session,"ID":input_id,"OUT.id":elmt_id}
                            # Adding "OUT.out" in key
                            new_dict = {"OUT.out."+key: value for key, value in custom_query.items()}
                            dafault_query.update(new_dict)
                            #print dafault_query
                            queryout = mdb_out.find_one(dafault_query,{"_id":0,"TD":0})
                            #print queryout
                            if queryout == None:
                                print "Issue Pattern Not matched"
                            else:
                                print "Issue Pattern  Matched"
                                # Update very lowest score in rank pattern
                                if last_score > score:
                                    last_score = score
                                #tmpdesc = hostname+" "+ip+" "+str(emon)+" "+str(etype)+" "+str(ename)+" "+str(custom_query)+" "+str(last_score)+" "+str(queryout.get("OUT"))
                                #desc = desc+"\n"+str(tmpdesc)
                                #print "Issue pattern matched > ",desc
                                mdb_out.update(dafault_query,{"$set": {"OUT.$.score":last_score,"OUT.$.note":'desc'}})
                    except Exception as e:
                        print ("mongo_search_score Error2>"+str(e))
            except Exception as e:
                print ("mongo_search_score Error1>"+str(e))
    except Exception as e:
        print("mongo_search_score Error>"+str(e))


mongo_search()