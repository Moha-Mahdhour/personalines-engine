import os
import logging
import uvicorn
import threading
from models import Task
from fastapi import FastAPI
from Collector import Collector
from Personalizator import Personlizator

# Create Collector
collector = Collector()
# Create FastAPI app
app = FastAPI()
# Create Personalizator
personalizator = Personlizator()



@app.post("/api")
def api(task: Task):
    if task.record.Status == "Init":
        collector.add_to_queue(task=task)
        logging.info(msg="\tInserted Into Collector Queue")
    elif task.record.Status == "Personalizing":
        personalizator.add_to_queue(task=task)
        logging.info(msg="\tInserted To Personalizator Queue")

    
if __name__ == "__main__":
    
    threading.Thread(target=personalizator.run, daemon=True ).start()
    threading.Thread(target=collector.run, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=10000)
