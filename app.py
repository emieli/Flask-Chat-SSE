from queue import Queue, Full
from flask import Flask, render_template, Response, request

"""
https://maxhalford.github.io/blog/flask-sse-no-deps/
"""

app = Flask(__name__)


class MessageAnnouncer:
    def __init__(self):
        self.listeners = []

    def listen(self):
        self.listeners.append(Queue(maxsize=5))
        return self.listeners[-1]

    def announce(self, msg):
        # We go in reverse order because we might have to delete an element
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except Full:
                del self.listeners[i]


announcer = MessageAnnouncer()


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/")
def post_message():
    """Takes message from a user and sends it to all listeners using SSE.
    The SSE message must use a specific format, as shown below.
    The data keyword is mandatory.
    The event keyword is optional."""
    user = request.form["user"]
    message = request.form["msg"]
    print(f"{user}: {message}")

    if "fuck" in message:
        """We send message as a "badword" event"""
        sse_message = f"event: badword\ndata: Please don't use bad words.\n\n"
    else:
        """This is a normal SSE message"""
        sse_message = f"data: {user}: {message}\n\n"

    announcer.announce(sse_message)

    """We don't need to return anything as request was made by AJAX"""
    return {}, 200


@app.get("/listen")
@app.get("/listen/<uuid>")
def listen(uuid=None):
    print(uuid)

    def stream():
        messages = announcer.listen()  # returns a Queue
        while True:
            msg = messages.get()  # blocks until a new message arrives
            yield msg

    return Response(stream(), mimetype="text/event-stream")
