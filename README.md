
## Setup
This project requires python 3. You can find installtion instructions [here](https://docs.python-guide.org/starting/installation/). You will also need ngrok to expose a local server so that Dialogflow can send requests to the local webhook. You can download ngrok [here](https://ngrok.com/download)

### Install Dependencies

It is reccomended to use a virtual environement. Below is the command to use `venv` which is included with python3 but you may also use virtualenv or pipenv if you prefer.

``` shell

# enter the backend directory
$ cd backend

# create the virtual environmnet
$ python3 -m venv env

# activate it
$ source env/bin/activate
```

Once activated you should see "backend" or something similar at the start of your terminal prompt.

#### Install requirements
With the virtualenv activated, run:

``` shell
$ pip install -e .
```


#### Expose Local Fullfillment URL
In a separate terminal, after downlaoding and installing ngrok, start ngrok to forward port 5000

``` shell
$ ./ngrok http 5000
```

You will then see something like

``` shell
Session Status                online
Account
Version                       2.2.8
Region                        United States (us)
Web Interface                 http://127.0.0.1:4040
Forwarding                    http://e1d5699f.ngrok.io -> localhost:5000
Forwarding                    https://e1d5699f.ngrok.io -> localhost:5000
```

1. Copy the **https** forwarding URL
2. Then navigate to the Fulfillment tab in the dialogflow console
3. Enable *Webhook* and ensure *Inline Editor* is disabled
4. Paste the copied URL into the URL field, and add **/assist** to the end
5. For example, with the above URL, we would paste `https://e1d5699f.ngrok.io/assist`

Note that you need to leave this terminal session running as you develop.
If you stop the ngrok process, you will simply need to restart it and replace the Dialogflow Fulfillment URL.

### Running the webhook (Flask app)
The flask app acts as the webhook in this project. This means that when Dialogflow receives a query from the user, it matches an **Intent** using its NLP, and then makes a request to our webhook containing the matched intent, **entities** (parameters), context, etc...

The webhook is then responible for carrying out the logic (or action functions) for the matched intent, and return a response to Dialogflow to be sent back to the user on whichever platform they are using.

To start the webhook, first set some environmnet variables by running the following in your terminal

``` shell
export FLASK_APP=autoapp:app
export FLASK_DEBUG=1
export FLASK_ENV='development'
export GOOGLE_APPLICATION_CREDENTIALS=service-account.json
export GOOGLE_CLOUD_PROJECT=test-county
```

Then to start the webhook:

```sh
 flask run
```

Now dialogflow will send requests to your local server as you interact with the bot.



## Development
TODO
