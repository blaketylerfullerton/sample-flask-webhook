from flask import Flask, request, jsonify
import openai
import os
# Set your OpenAI API key

openai.api_key = os.getenv('OPENAI_API_KEY')

from flask import render_template

app = Flask(__name__)


@app.route("/")
def hello_world():
    return render_template("index.html")

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        data = request.json
        # Extract the transcript from the webhook data
        transcript = data['call']['transcript']
        # Check if API key is set
        if not openai.api_key:
            return jsonify({"status": "error", "message": "OpenAI API key not set"}), 500
        # Send the transcript to OpenAI for summarization
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes call transcripts."},
                    {"role": "user", "content": f"Please summarize the following call transcript:\n\n{transcript}"}
                ]
            )
            # Extract the summary from the OpenAI response
            summary = response.choices[0].message['content']
            # You can now store or process the summary as needed
            print("Call Summary:", summary)
            # Optionally, you can add the summary to the response
            data['call']['summary'] = summary
            return jsonify({"status": "success", "data": data}), 200
        except Exception as e:
            print(f"Error in OpenAI API call: {str(e)}")
            return jsonify({"status": "error", "message": "Failed to generate summary"}), 500
    else:
        return jsonify({"status": "error", "message": "Method not allowed"}), 405

if __name__ == "__main__":
    app.run(debug=True)