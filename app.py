from flask import Flask, request, jsonify

from flask import render_template

app = Flask(__name__)


@app.route("/")
def hello_world():
    return render_template("index.html")

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        print("Received data:")
        print(request.json)
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error", "message": "Method not allowed"}), 405


if __name__ == "__main__":
    app.run(debug=True)