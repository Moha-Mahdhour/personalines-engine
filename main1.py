import os
import logging
import threading
from models import Task
from Collector import Collector
from Personalizator import Personlizator
collector = Collector()
personalizator = Personlizator()
def distrubtor(task):
    if task.record.Status == "Init":
        collector.add_to_queue(task=task)
        logging.info(msg="\tInserted Into Collector Queue")
    elif task.record.Status == "Personalizing":
        personalizator.add_to_queue(task=task)
        logging.info(msg="\tInserted To Personalizator Queue")
def main():
    from realtime.connection import Socket

    SUPABASE_ID = os.environ.get("SUPABASE_ID")
    API_KEY = os.environ.get("SUPABASE_SECRET")

    URL = f"wss://{SUPABASE_ID}.supabase.co/realtime/v1/websocket?apikey={API_KEY}&vsn=1.0.0"
    s = Socket(URL)
    s.connect()

    channel_1 = s.set_channel("realtime:public:tasks")
    channel_1.join().on("INSERT", distrubtor)
    channel_1.join().on("UPDATE", distrubtor)
    try:
        print("Starting to listen...")
        s.listen()  # Assuming listen is an async function
    except Exception as e:
        print(f"An error occurred: {e}")
        
if __name__ == "__main__":
    threading.Thread(target=personalizator.run, daemon=True).start()
    threading.Thread(target=collector.run, daemon=True).start()
    main()
