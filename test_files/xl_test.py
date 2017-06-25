import pandas as pd
import csv
import json

xl = pd.ExcelFile("E:\\in.xlsx")
df1 = xl.parse('input')
ID = list(set((df1.get("ID"))))
full_list = []

for i in ID:
    local_list = []
    xx = ""
    for index, row in df1.iterrows():
     #print row['IP'] , row['_id'], row['_type'] , row['_name'] , row['_monitor'], row['_rank']
         if row["ID"] == i:
             a = json.dumps({"id":int(row["_id"]),"type": row["_type"] , "name": row["_name"] , "monitor":row["_monitor"], "rank": json.loads(row["_rank"])})
             local_list.append(a)
             xx = row
    full_list.append({"ID":int(xx["ID"]),"Hostname": str(xx["Hostname"]),"IP":str(xx["IP"]),"Authentication":xx["Authentication"],
      "Model":str(xx["Model"]),"Mode":str(xx["Mode"]),"timeout":int(xx["timeout"]),"Monitoring_obj":local_list})





for d in full_list:
            # Json loads used to convert string to array object
           d.update({"INID":22,"Monitoring_obj":d.get("Monitoring_obj")})

for t in full_list:
    print t

##keys = full_list[0].keys()
##with open('d:\\people.csv', 'wb') as output_file:
##    dict_writer = csv.DictWriter(output_file, keys)
##    dict_writer.writeheader()
##    dict_writer.writerows(full_list)
