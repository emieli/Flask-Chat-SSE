from queue import Queue, Full
from flask import Flask, render_template, Response, request
from datetime import datetime
import json

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
        return sorted(users)

    def broadcast(self, message) -> None | ValueError:
        """Send message to all listeners"""

        if not message:
            raise ValueError("No data to send")

        for uuid in reversed(list(listeners)):
            """We loop in reverse as disconnected listeners are removed"""
            try:
                listeners[uuid].queue.put_nowait(message)
            except Full:
                username = listeners[uuid].username
                del listeners[uuid]
                message = new_message(f"{username} connection timed out.")
                announcer.broadcast(message)
                chat_history.append(message)
                self.update_userlist()

    def unicast(self, uuid, message) -> None | ValueError:
        """Send message to a specific listener
        Multiple lines of data must be a list of strings
        A single line of data can be a string."""

        """Input validation"""
        if not message:
            raise ValueError("No message to send")

        """Send SSE message"""
        try:
            listeners[uuid].queue.put_nowait(message)
        except Full:
            username = listeners[uuid].username
            del listeners[uuid]
            message = new_message(f"{username} connection timed out.")
            announcer.broadcast(message)
            chat_history.append(message)

    def update_userlist(self):
        users = " ".join(self.users)
        sse_message = "event: userlist\n"
        sse_message += f"data: {users}\n\n"
        self.broadcast(sse_message)


class CommandHandler:
    def __init__(self, message: str, uuid: str):
        self.uuid = uuid
        command, *args = message.split()
        match command:
            case "!username":
                self.username(args)
            case "!help":
                self.help()
            case "!whoami":
                self.whoami()
            case _:
                self.default()

    def default(self):
        message = "Unknown command. Enter !help to see available commands."
        sse_message = new_message(message, send_timestamp=False)
        announcer.unicast(self.uuid, sse_message)

    def help(self):
        message = [
            "Welcome to Chat, created by Golle.",
            "Available commands:",
            "  !username - Change your username",
            "  !whoami   - View your current username",
        ]
        sse_message = new_message(message, send_timestamp=False)
        announcer.unicast(self.uuid, sse_message)

    def username(self, args):
        """Process the !username commmand"""
        if len(args) != 1:
            message = [
                "This command allow you to change your username, with some restrictions:",
                " - It may not contain any spaces",
                " - It may not be longer than 12 characters",
                "Example: !username Guest666",
            ]
            sse_message = new_message(message, send_timestamp=False)
            announcer.unicast(self.uuid, sse_message)
            return

        """Update username on server"""
        new_username = args[0][:12]
        username = listeners[self.uuid].username
        listeners[self.uuid].username = new_username

        """Update username on client"""
        announcer.update_userlist()
        sse_message = new_username_message(new_username)
        announcer.unicast(self.uuid, sse_message)

        """Share new username with chat"""
        sse_message = new_message(f"{username} changed name to {new_username}")
        announcer.broadcast(sse_message)
        chat_history.append(sse_message)

    def whoami(self):
        message = f"Your username is {listeners[self.uuid].username}."
        sse_message = new_message(message, send_timestamp=False)
        announcer.unicast(self.uuid, sse_message)


def new_message(message: str | list, user: str = "", send_timestamp: bool = True) -> str:
    """Generate new message in SSE format"""
    EVENT = "new_message"
    END_OF_MESSAGE = "\n\n"
    sse_message = f"event: {EVENT}\n"

    data = {}
    if user:
        data["user"] = user
    if send_timestamp:
        data["timestamp"] = datetime.now().timestamp()

    if isinstance(message, str):
        data["message"] = message
    if isinstance(message, list):
        data["message"] = "\n".join(message)

    sse_message += f"data: {json.dumps(data)}"
    sse_message += END_OF_MESSAGE

    return sse_message


def new_username_message(username: str) -> str:
    """Create 'new username' message in SSE format."""
    EVENT = "new_username"
    END_OF_MESSAGE = "\n\n"
    sse_message = f"event: {EVENT}\n"
    sse_message += f"data: {username}"
    sse_message += END_OF_MESSAGE
    return sse_message


chat_history = []
listeners = dict()
announcer = MessageAnnouncer()


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/")
def message_from_user():
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
        sse_message = new_message("Please don't swear.", send_timestamp=False)
        announcer.unicast(uuid, sse_message)
        return {}, 200

    if message.startswith("!"):
        sse_message = new_message(message)
        announcer.unicast(uuid, sse_message)
        commandhandler = CommandHandler(message, uuid)
        return {}, 200

    """This is a normal SSE message"""
    sse_message = new_message(message, user)
    announcer.broadcast(sse_message)
    return {}, 200


@app.get("/listen")
@app.get("/listen/<uuid_and_user>")
def listen(uuid_and_user=None):
    """Establish a new listener session, for server to continue sending messages.
    Each listener is identified by its unique UUID, allowing the server to send
    messages to a specific listener.

    When connecting, the listener also sends the username save in its browser
    localStorage. If the value is null, the server generates a GuestNNN name."""

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

    # This doesn't work because we don't log 'user joined' messages to chat_history.
    sse_message = new_message(f"{username} has joined the chat")
    announcer.broadcast(sse_message)
    chat_history.append(sse_message)

    def stream():
        listener = Listener(uuid, username)
        listeners[uuid] = listener
        messages = listener.queue

        """Inform client about its new username"""
        sse_message = new_username_message(username)
        announcer.unicast(uuid, sse_message)

        """Send last 100 user messages from chat history in a single SSE message"""
        sse_message = ""
        for message in chat_history[-100:]:
            sse_message += message
        announcer.unicast(uuid, sse_message)

        """Send !help server message"""
        sse_message = new_message(
            f"Welcome {username}! Enter !help to see available commands.",
            send_timestamp=False,
        )
        announcer.unicast(uuid, sse_message)
        announcer.update_userlist()

        while True:
            msg = messages.get()  # blocks until a new message arrives
            yield msg

    return Response(stream(), mimetype="text/event-stream")
