import time
import os
import json
import queue
import asyncio
import logging
from supa import supa
from models import Task, LinkedInProfileModel
from csv import DictWriter, DictReader
from proxycurl.asyncio import Proxycurl, do_bulk


class Collector:
    
    def __init__(self) -> None:
        self.queue = queue.Queue()
        self.proxycurl = Proxycurl(api_key=os.environ.get("PROXYCURL_SECRET"))
        print("Collector Created....")
        
    def add_to_queue(self, task:Task):
        self.queue.put(task)
        
    def collect_info(self,csvFile, task: Task):
        with open(csvFile) as f:
            csv = DictReader(f)
            bulk_linkedin_person_data = []
            for line in csv:
                bulk_linkedin_person_data.append(
                    (self.proxycurl.linkedin.person.get, {'linkedin_profile_url': line[task.record.LinkedinField]}))
                
        
        results = asyncio.run(do_bulk(bulk_linkedin_person_data))
        return results
    
    def format_info(self, results, csvFile, task: Task, supbasePath):
        
        
        with open(csvFile) as f:
            
            new_list = []
            csv = DictReader(f)
            for line, result in zip(csv, results):
                if not result.success:
                    line["Description"] = "Not Found"
                    continue
                profile = LinkedInProfileModel(**(result.value))
                line["Description"] = f"""{str(profile)}"""
                new_list.append(line)
            
        if not len(new_list):
            supa.table("tasks").update({
                        "Status": "Error"
                    }).eq("id", task.record.id).execute()
            return
        
        csvFile = csvFile.split(".csv")[0] + "-formatted.csv"
        
        with open(csvFile, "w") as f:
            csv = DictWriter(f, fieldnames=new_list[0].keys())
            csv.writeheader()
            csv.writerows(new_list)
        
        with open(csvFile, "rb") as f:
                try:
                    supa.storage.from_("Users").upload(file=f, path=supbasePath.split(".csv")[0]+ "-formatted.csv", file_options={"content-type": "text/csv"})
                    supa.table("tasks").update({
                        "Status": "Personalizing"
                    }).eq("id", task.record.id).execute()
                except:
                    supa.table("tasks").update({
                        "Status": "Error"
                    }).eq("id", task.record.id).execute()
                    print("Error in personlizing uploading to storage")
                
        
            
            
            
            
                

        
    def run(self):
        while True:
            if self.queue.empty():
                time.sleep(1)
                continue
            
            task: Task = self.queue.get()
            
            # Setting the status to Searching
            supa.table("tasks").update({
                "Status": "Searching"
            }).eq("id", task.record.id).execute()
            
            path = f"Filing/{task.record.UserID}/{task.record.id}"
            supabasePath = f"{task.record.UserID}/{task.record.id}"
            filename = task.record.FileName
            full_path = path + "/" + filename
            supabasePath = supabasePath + "/" + filename

            time.sleep(1.5) # Wait maybe the file takes time

            if not os.path.exists(path):
                os.makedirs(path)
                
            with open(full_path, "wb+") as f:
                done = False
                error = False
                index = 0
                while not done: # Better Error hadnling until the file is returned 
                    try:
                        res = supa.storage.from_("Users").download(supabasePath)
                        f.write(res)
                        done = True
                        break
                    except Exception as e:
                        print("Error Can't find the file")
                        time.sleep(5)
                        if index > 2:
                            supa.table("tasks").update({
                                "Status": "Error",
                                "error_message": e.__repr__()
                            }).eq("id", task.record.id).execute()
                            error = True
                            break
                        index += 1
                if error:
                    continue
                        
            collected_info: list = self.collect_info(full_path, task)
            self.format_info(collected_info, full_path, task, supabasePath)
            logging.info(msg=f"Finished Collecting for {task.record.id}")
