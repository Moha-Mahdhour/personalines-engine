import os
import csv
import json
import time
import random
import requests
import threading
import concurrent.futures
from supa import supa
from queue import Queue 
from models import Task
from ExamplesMaker import ExampleMaker
from PersonlizatorScripts import UserMessageV5, SystemMessageV1
from langchain.schema import (
    HumanMessage,
    SystemMessage
)

class Personlizator:
    
    def __init__(self):
        self.queue = Queue()
        # OpenAI headers
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + os.environ["OPENAI_API_KEY"],
        }
        # OpenAI Json Data
        self.json_data = {
        'model': os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
        
        'temperature': 1, # was 25 testing  1 now
        }
        self.lock = threading.Lock()
        self.exampleMaker = ExampleMaker()
        self.csv_file = []
        print("Personlizator Created...")
    
    def add_to_queue(self, task:Task):
        self.queue.put(task)
        
    def get_file(self, task):
        
        filepath = f"Filing/{task.record.UserID}/{task.record.id}/{task.record.FileName}".split(".")[0]+"-formatted.csv"
        file = open(filepath, "r")
        csvFile = csv.DictReader(file)
        csvFile = list(csvFile)
        file.close()
        return csvFile
        
    def async_generate(self, line):
        
        if line["Description"] == "Not Found":
            return

        if len(line["Description"]) / 4 > 4000:
            line["Description"] = line["Description"][0:10000] + "}"

        messages = [
            SystemMessage(content=SystemMessageV1).content,
            HumanMessage(content=UserMessageV5.replace("INSERT", self.exampleMaker.get_examples_string(7)) + f"""\njson = {line["Description"]}""").content
        ]
        messages = [
            {
                "role": "system",
                "content": messages[0]
            },
            {
                "role": "user",
                "content": messages[1]
            }
        ]
        json_data =self.json_data.copy()
        json_data["messages"] = messages
        
        done = False
        while not done:
            try:
                response = requests.post('https://api.openai.com/v1/chat/completions', headers=self.headers, json=json_data, timeout=20)
                response_data = json.loads(response.content.decode('utf-8'))
                if response_data.get("error"):
                    time.sleep(random.random()*7)
                    print(response_data.get("error"))
                else:
                    done=True
            except:
                time.sleep(random.random() * 6)

        with self.lock:
            response_data = json.loads(response.content.decode('utf-8'))
            line["Personalization"] = response_data["choices"][0]["message"]["content"]
            del line["Description"]
            self.csv_file.append(line)
        
        time.sleep(39)
        
    def process_list(self, csvFile):
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=80) as executor:
            
            executor.map(self.async_generate, csvFile)
            
    def writeFile(self, task: Task):
        
        with open(f"Filing/{task.record.UserID}/{task.record.id}/{task.record.FileName}".split(".")[0]+"-Final.csv", mode='w') as csv_file:
        
                if not len(self.csv_file):
                    exit()
                    
                fieldnames = self.csv_file[0].keys()
                
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.csv_file)
        
    def run(self):
       while True:
            
            if self.queue.empty():
                time.sleep(10)
                continue
            
            self.csv_file = []
            
            task: Task = self.queue.get()
            
            csvFile = self.get_file(task)
            
            self.process_list(csvFile)
            
            self.writeFile(task)
            
            filepath = f"Filing/{task.record.UserID}/{task.record.id}/{task.record.FileName}".split(".")[0]+"-Final.csv"
            supabase_path = f"{task.record.UserID}/{task.record.id}/{task.record.FileName}".split(".")[0]+"-formatted-Final.csv"
            with open(filepath, "rb") as f:
                try:
                    supa.storage.from_("Users").upload(file=f, path=supabase_path, file_options={"content-type": "text/csv"})
                except Exception as e:
                    print("Error in personlizing uploading to storage", e)
                    supa.table("tasks").update({
                        "Status": "Error",
                        "error_message": str(e)
                    }).eq("id", task.record.id).execute()
            
            supa.table("tasks").update({
                "Status": "Completed"
            }).eq("id", task.record.id).execute()
            
            
            
            self.csv_file = []
            time.sleep(10)
            
            

            