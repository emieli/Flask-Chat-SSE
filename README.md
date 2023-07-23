# A Flask Chat-App with SSE
I've used Flask for different projects over the years and I always struggle with making the webpages dynamic. I recently stumbled across a HTTP technology called Server-Side Events (SSE) which allows a streaming connection to be setup, allowing the Web-server to continue sending data to the client, even after the webpage had fully loaded.

I have tried other solutions for this before, including Websockets and SocketIO but they were always tricky to implement. This attempt will be using SSE instead. I base my Flask SSE implementation on "https://maxhalford.github.io/blog/flask-sse-no-deps/" written by a very talened author. 

Right off the bat SSE has one problem though, and that's sending information to specific clients. In my chat program I want users to communicate with each other, but I also want to allow server messages to be directed to a specific user. For example, if a user tries to enter a swearword in a message, instead of broadcasting that message the server should respond with a "don't swear please" back to only that user. I don't yet have a solution to that problem.

Note that we need to use TLS for SSE to work, so we need an Nginx instance in front. I should probably document this...

# Installation

    $ apt install python3-pip python3-venv
    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip install --upgrade pip
    $ pip install -r requirements.txt

# Running Flask in debug:

    $ flask run --host=0.0.0.0 --debug

# Running Flask in "prod":
This only works on Linux systems that use the systemd service setup. It works on Debian, Ubuntu should also work.
This isn't a true production setup as we're using the builtin Flask development server. To go truly production, one should use Gunicorn or similar.

    $ cat /etc/systemd/system/flask_webserver.service
    [Unit]
    Description=Flask Webserver
    After=network.target

    [Service]
    WorkingDirectory=/opt/chat
    ExecStart=/opt/chat/venv/bin/python -m flask run --host=0.0.0.0
    Restart=always

    [Install]
    WantedBy=multi-user.target

    $ sudo systemctl daemon-reload
    $ sudo systemctl start flask_webserver.service

### Show logs:

    $ sudo journalctl -f -u flask_webserver.service
    Jul 23 17:22:31 chat-1 python[17982]:  * Debug mode: off
    Jul 23 17:22:31 chat-1 python[17982]: WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
    Jul 23 17:22:31 chat-1 python[17982]:  * Running on all addresses (0.0.0.0)
    Jul 23 17:22:31 chat-1 python[17982]:  * Running on http://127.0.0.1:5000

