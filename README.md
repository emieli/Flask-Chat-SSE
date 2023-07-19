# A Flask Chat-App with SSE
I've used Flask for different projects over the years and I always struggle with making the webpages dynamic. I recently stumbled across a HTTP technology called Server-Side Events (SSE) which allows a streaming connection to be setup, allowing the Web-server to continue sending data to the client, even after the webpage had fully loaded.

I have tried other solutions for this before, including Websockets and SocketIO but they were always tricky to implement. This attempt will be using SSE instead. I base my Flask SSE implementation on "https://maxhalford.github.io/blog/flask-sse-no-deps/" written by a very talened author. 

Right off the bat SSE has one problem though, and that's sending information to specific clients. In my chat program I want users to communicate with each other, but I also want to allow server messages to be directed to a specific user. For example, if a user tries to enter a swearword in a message, instead of broadcasting that message the server should respond with a "don't swear please" back to only that user. I don't yet have a solution to that problem.

# Installation

    $ apt install python3-pip python3-venv
    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip install --upgrade pip
    $ pip install -r requirements.txt

# Running Flask:

    $ flask run --host=0.0.0.0

Note that we need to use TLS for SSE to work, so we need an Nginx instance in front. I should probably document this...