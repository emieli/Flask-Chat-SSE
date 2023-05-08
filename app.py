from queue import Queue, Full
from flask import Flask, render_template, Response, request

"""
https://maxhalford.github.io/blog/flask-sse-no-deps/
"""

app = Flask(__name__)


class MessageAnnouncer:
    def __init__(self):
        self.listeners = dict()

    def listen(self, uuid):
        """Add a new listener"""
        self.listeners[uuid] = Queue(maxsize=5)
        return self.listeners[uuid]

    def unicast(self, msg, uuid):
        """Send message to a specific listener"""
        try:
            self.listeners[uuid].put_nowait(msg)
        except Full:
            del self.listeners[uuid]

    def broadcast(self, msg):
        """Send message to all listeners"""
        for i in reversed(list(self.listeners)):
            """We loop in reverse as disconnected listeners are removed"""
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
    uuid = request.form["uuid"]
    print(f"{user}: {message}")

    if "fuck" in message:
        """We send message as a "badword" event"""
        sse_message = f"event: badword\ndata: Please don't swear.\n\n"
        announcer.unicast(sse_message, uuid)
    else:
        """This is a normal SSE message"""
        sse_message = f"data: {user}: {message}\n\n"
        announcer.broadcast(sse_message)

    """We don't need to return anything as request was made by AJAX"""
    return {}, 200


@app.get("/listen")
@app.get("/listen/<uuid>")
def listen(uuid=None):
    """A new listener session is established, allowing server to send messages"""

    def stream():
        messages = announcer.listen(uuid)  # returns a Queue
        while True:
            msg = messages.get()  # blocks until a new message arrives
            yield msg

    return Response(stream(), mimetype="text/event-stream")
