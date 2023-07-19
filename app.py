from queue import Queue, Full
from flask import Flask, render_template, Response, request

"""
https://maxhalford.github.io/blog/flask-sse-no-deps/
"""

app = Flask(__name__)


class MessageAnnouncer:
    def __init__(self):
        self.listeners = dict()
        self.chat_history = []

    @property
    def users(self) -> list:
        """Return list of active users"""
        users = [listener["username"] for listener in announcer.listeners.values()]
        return users

    def listen(self, uuid: str, username: str) -> Queue:
        """Add a new listener"""
        self.listeners[uuid] = {
            "message_queue": Queue(maxsize=5),
            "username": username,
        }
        self.update_userlist()
        return self.listeners[uuid]["message_queue"]

    def unicast(self, msg, uuid):
        """Send message to a specific listener"""
        try:
            self.listeners[uuid]["message_queue"].put_nowait(msg)
        except Full:
            del self.listeners[uuid]
            self.update_userlist()

    def broadcast(self, msg):
        """Send message to all listeners"""
        print(msg.strip())
        print()
        if msg.startswith("data: "):
            self.chat_history.append(msg.replace("data: ", ""))
        for i in reversed(list(self.listeners)):
            """We loop in reverse as disconnected listeners are removed"""
            try:
                self.listeners[i]["message_queue"].put_nowait(msg)
            except Full:
                del self.listeners[i]
                self.update_userlist()

    def update_userlist(self):
        event = "event: userlist"
        users = "\ndata: ".join(self.users)
        self.broadcast(f"{event}\ndata: {users}\n\n")


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
    message = request.form["message"]
    uuid = request.form["uuid"]
    user = announcer.listeners[uuid]["username"]

    if not uuid in announcer.listeners:
        """Must be a registered listener to send messages"""
        return {}, 403

    if "fuck" in message:
        """We send message as a "badword" event"""
        sse_message = f"data: Server: Please don't swear.\n\n"
        announcer.unicast(sse_message, uuid)
        return {}, 200

    if message == "!username" or message.startswith("!username "):
        """Update username"""
        message_split = message.split()
        if len(message_split) != 2:
            help_message = f"data: {message}\n"
            help_message += "data: This command allow you to change your username. It may not contain any spaces\n"
            help_message += "data: Example: !username Guest666\n"
            announcer.unicast(help_message, uuid)
            return {}, 200
        new_username = message_split[-1]
        announcer.listeners[uuid]["username"] = new_username
        announcer.broadcast(f"data: {user} changed name to {new_username}\n\n")
        announcer.update_userlist()
        announcer.unicast(f"event: newUsername\ndata: {new_username}\n\n", uuid)
        return {}, 200

    """This is a normal SSE message"""
    formatted_message = f"{user}: {message}"
    # print(formatted_message)
    sse_message = f"data: {formatted_message}\n\n"
    announcer.broadcast(sse_message)
    return {}, 200


@app.get("/listen")
@app.get("/listen/<uuid_and_user>")
def listen(uuid_and_user=None):
    """Establish a new listener session, allowing server to send messages.
    Each listener is identified by its unique UUID, allowing the server
    to send messages to only chat client.

    When connecting, the listener also sends the username save in its
    browser localStorage. If the value is null, the server generates a
    GuestNNN name.
    """

    if not uuid_and_user:
        return "Error: uuid missing."

    if not "&" in uuid_and_user:
        return "Error: incorrect format."

    uuid, username = uuid_and_user.split("&")

    """If username is not set, generate one."""
    if username == "null":
        i = 0
        while True:
            i += 1
            guest_username = f"Guest{i:03d}"
            if not guest_username in announcer.users:
                username = guest_username
                break

    def stream():
        announcer.broadcast(f"data: {username} has joined the chat\n\n")
        messages = announcer.listen(uuid, username)  # returns a Queue
        last_hundred_messages = "\ndata: ".join(announcer.chat_history[-100:])
        announcer.unicast(f"event: newUsername\ndata: {username}\n\n", uuid)
        announcer.unicast(f"event: connected\ndata: {last_hundred_messages}\n\n", uuid)
        while True:
            msg = messages.get()  # blocks until a new message arrives
            yield msg

    return Response(stream(), mimetype="text/event-stream")
