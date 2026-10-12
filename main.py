from contextvars import ContextVar
import threading

x = ContextVar("x", default="unset")

def worker(name):
    x.set(name)
    print(name, "sees", x.get())

threading.Thread(target=worker, args=("A",)).start()
threading.Thread(target=worker, args=("B",)).start()
print("main sees", x.get())   # "unset": the threads never touched main's value