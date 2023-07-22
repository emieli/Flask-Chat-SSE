from queue import Queue, Full
from flask import Flask, render_template, Response, request

"""
https://maxhalford.github.io/blog/flask-sse-no-deps/
"""

app = Flask(__name__)


class Listener:
    def __init__(self, uuid: str, username: str):
        self.queue = Queue(maxsize=5)
        self.username = username
        self.uuid = uuid


class MessageAnnouncer:
    @property
    def users(self) -> list[str]:
        """Return list of active users"""
        users = [listener.username for listener in listeners.values()]
        return users

    def build_sse_message(self, data: str | list, event: str = "") -> None | ValueError:
        """Format data into SSE message."""
        message = ""
        if event:
            message += f"event: {event}\n"

        if isinstance(data, list):
            """Multiple lines of data"""
            message += "data: " + "\ndata: ".join(data)
        elif isinstance(data, str):
            """A single line of data"""
            if "\n" in data:
                raise ValueError("The data string must be a single line")
            message += f"data: {data}"

        print(message + "\n")
        message += "\n\n"  # To signal that we have reached the end of the message
        return message

    def broadcast(self, data: str | list, event: str = "") -> None | ValueError:
        """Send message to all listeners"""

        """Input validation"""
        if not data:
            raise ValueError("No data to send")

        if not event:
            chat_history.append(data)

        """Build the SSE message"""
        message = self.build_sse_message(data, event)

        for i in reversed(list(listeners)):
            """We loop in reverse as disconnected listeners are removed"""
            try:
                listeners[i].queue.put_nowait(message)
            except Full:
                del listeners[i]
                self.update_userlist()

    def unicast(self, data: str | list, uuid: str, event: str = "") -> None | ValueError:
        """Send message to a specific listener
        Multiple lines of data must be a list of strings
        A single line of data can be a string."""

        """Input validation"""
        if not uuid:
            raise ValueError("UUID must be given")
        if not data:
            raise ValueError("No data to send")

        """Build the SSE message"""
        message = self.build_sse_message(data, event)

        """Send SSE message"""
        try:
            listeners[uuid].queue.put_nowait(message)
        except Full:
            del listeners[uuid]
            self.update_userlist()

    def update_userlist(self):
        self.broadcast(self.users, event="userlist")


class CommandHandler:
    def __init__(self, message: str, uuid: str):
        self.uuid = uuid
        command, *args = message.split()
        match command:
            case "!username":
                self.username(args)
            case "!help":
                message = [
                    "Welcome to Chat, created by Golle.",
                    "Available commands:",
                    "  !username - Change your username",
                ]
                announcer.unicast(message, uuid)
            case _:
                message = [
                    f"{message} is an unknown command.",
                    "Enter !help to see available commands.",
                ]
                announcer.unicast(message, uuid)

    def username(self, args):
        """Process the !username commmand"""
        if len(args) != 1:
            help_message = [
                f"!username {' '.join(args)}",
                "This command allow you to change your username. It may not contain any spaces",
                "Example: !username Guest666",
            ]
            announcer.unicast(help_message, self.uuid)
            return

        username = listeners[self.uuid].username
        new_username = args[0]

        listeners[self.uuid].username = new_username
        announcer.broadcast(f"{username} changed name to {new_username}")
        announcer.update_userlist()
        announcer.unicast(new_username, self.uuid, event="newUsername")


chat_history = ["line one", "line two"]
listeners = dict()
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
    user = listeners[uuid].username

    if not uuid in listeners:
        """Must be a registered listener to send messages"""
        return {}, 403

    if "fuck" in message:
        """We send message as a "badword" event"""
        message = "Server: Please don't swear."
        announcer.unicast(message, uuid)
        return {}, 200

    if message.startswith("!"):
        commandhandler = CommandHandler(message, uuid)
        return {}, 200

    """This is a normal SSE message"""
    formatted_message = f"{user}: {message}"
    announcer.broadcast(formatted_message)
    return {}, 200


@app.get("/listen")
@app.get("/listen/<uuid_and_user>")
def listen(uuid_and_user=None):
    """Establish a new listener session, for server to continue sending messages.
    Each listener is identified by its unique UUID, allowing the server to send
    messages to a specific listener.

    When connecting, the listener also sends the username save in its browser
    localStorage. If the value is null, the server generates a GuestNNN name.
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

    announcer.broadcast(data=f"{username} has joined the chat")

    def stream():
        listener = Listener(uuid, username)
        listeners[uuid] = listener
        messages = listener.queue

        last_hundred_messages = chat_history[-100:]
        announcer.unicast(username, uuid, event="newUsername")
        announcer.unicast(last_hundred_messages, uuid, event="connected")
        announcer.unicast("Enter !help to see available commands.", uuid)
        announcer.update_userlist()

        while True:
            msg = messages.get()  # blocks until a new message arrives
            yield msg

    return Response(stream(), mimetype="text/event-stream")
