from flask import Flask, request, jsonify
import openai
import os
from datetime import datetime, timedelta
import requests


openai.api_key = os.getenv('OPENAI_API_KEY')
# Set up Airtable
AIRTABLE_BASE_KEY = os.getenv('AIRTABLE_BASE_KEY')
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME')
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')

#GHL Data
GHL_API_KEY = os.getenv('GHL_API_KEY')
GHL_LOCATION_ID = os.getenv('GHL_LOCATION_ID')
FORWARD_URL = 'https://services.leadconnectorhq.com/hooks/dX3FHZlxkSxr6Rt4xWhT/webhook-trigger/be4a38de-50d0-4c5a-94c7-d88f2281c4f5'  # URL to forward the webhook to


AIRTABLE_URL = f"https://api.airtable.com/v0/appONw8OOzv9YX4yT/Call%20Logs"
GHL_API_URL = "https://rest.gohighlevel.com/v1/opportunities/"

from flask import render_template

app = Flask(__name__)

@app.route("/")
def hello_world():
    return render_template("index.html")

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        data = request.json
        print(data)
         # Check if the event is 'call_ended'
        if data.get('event') != 'call_ended':
            return jsonify({"status": "success", "message": "Event ignored"}), 200
        # Extract the transcript from the webhook data
        transcript = data['call']['transcript']
        call_data = data['call']

        # Check if API key is set
        if not openai.api_key:
            return jsonify({"status": "error", "message": "OpenAI API key not set"}), 500
        # Send the transcript to OpenAI for summarization
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes call transcripts."},
                    {"role": "user", "content": f'''# Liv Forever Health: Call Analysis and Data Extraction Prompt

                        Analyze the following customer service call transcript for Liv Forever Health, handled by the AI voice assistant Jessica. Provide a structured summary with the following categories:

                        ## Call Overview:
                        - Summarize the main purpose of the call in 1-2 sentences.

                        ## Caller Information:
                        - List key details about the caller (e.g., name, reason for calling).
                        - Enumerate the main questions or requests made by the caller.

                        ## AI Assistant (Jessica) Actions:
                        - List the key information provided by Jessica.
                        - Identify any service recommendations or consultation suggestions made.

                        ## Call Flow:
                        - Outline the major topics discussed, in order.
                        - Note any transitions or shifts in the conversation.

                        ## Compliance and Protocol Adherence:
                        - Evaluate Jessica's adherence to the prescribed script and HIPAA compliance.
                        - Note if consent for call recording was obtained.
                        - Confirm if AI assistant status was disclosed.

                        ## Data Collection:
                        - List all information collected from the caller.
                        - Note any instances where health-specific information was successfully avoided.

                        ## Service Area Interest:
                        - Identify which Liv Forever Health service area(s) the caller expressed interest in.

                        ## AI Assistant Performance:
                        - Evaluate Jessica's overall performance in handling the call.
                        - Identify instances of good customer service or areas for improvement.
                        - Note any mistakes or inconsistencies in the information provided.

                        ## Call Outcome:
                        - State whether the caller's questions were answered satisfactorily.
                        - Mention if a consultation was scheduled or if follow-up is needed.

                        ## Areas for Improvement:
                        - Suggest 2-3 ways the call handling could be improved.

                        Keep each category concise, using bullet points where appropriate. Aim for a total summary length of about 300-350 words.

                        ## Data Extraction:
                        Extract and list the following specific data points:
                        - Caller's full name
                        - Caller's contact information (email or phone)
                        - Preferred contact method
                        - Best time for team to contact
                        - Service area of interest
                        - Preference for virtual or in-person consultation
                        - How they heard about Liv Forever Health

                        Note: Ensure that no specific health information is included in the extracted data.\n\n{transcript}'''}
                ]
            )
            summary = response.choices[0].message['content']
            data['call']['summary'] = summary

            start_time = datetime.fromtimestamp(call_data['start_timestamp'] / 1000)
            end_time = datetime.fromtimestamp(call_data['end_timestamp'] / 1000)
            duration = end_time - start_time
            duration_str = f"{duration.seconds // 60}m {duration.seconds % 60}s"

            # Prepare data for Go High Level
            ghl_data = {
                "name": f"Call from {call_data.get('from_number', 'Unknown')}",
                "monetaryValue": 0,  # Set an appropriate value if available
                "pipelineStageId": "",  # Set the appropriate pipeline stage ID
                "status": "open",
                "source": "Phone Call",
                "customFields": [
                    {"key": "call_date", "field_value": start_time.isoformat()},
                    {"key": "call_duration", "field_value": duration_str},
                    {"key": "call_summary", "field_value": summary},
                    {"key": "call_transcript", "field_value": transcript},
                    {"key": "recording_url", "field_value": call_data.get('recording_url', '')},
                    {"key": "caller_number", "field_value": call_data.get('from_number', '')},
                    {"key": "end_reason", "field_value": call_data.get('disconnection_reason', '')},
                    {"key": "call_sid", "field_value": call_data.get('metadata', {}).get('twilio_call_sid', '')}
                ]
            }

            # Send data to Go High Level
            headers = {
                "Authorization": f"Bearer {GHL_API_KEY}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
            ghl_response = requests.post(f"{GHL_API_URL}?locationId={GHL_LOCATION_ID}", json=ghl_data, headers=headers)
            if ghl_response.status_code == 200:
                print("Data successfully sent to Go High Level")
            else:
                print(f"Failed to send data to Go High Level. Status code: {ghl_response.status_code}")
                print(f"Response: {ghl_response.text}")

            return jsonify({"status": "success", "data": data}), 200
        except Exception as e:
            print(f"Error in API call: {str(e)}")
            return jsonify({"status": "error", "message": "Failed to process call data"}), 500
    else:
        return jsonify({"status": "error", "message": "Method not allowed"}), 405

@app.route('/forward-webhook', methods=['POST'])
def forward_webhook():
    if request.method == 'POST':
        data = request.json
        transcript = data.get('transcript', '')

        if data.get('event') != 'call_ended':
            print("Not call ended..")
            return jsonify({"status": "success", "message": "Event ignored"}), 200

        if not transcript:
            return jsonify({"status": "error", "message": "No transcript provided"}), 400

        if should_forward(transcript):
            # Forward the webhook
            try:
                response = requests.post(FORWARD_URL, json=data)
                if response.status_code == 200:
                    print("Forwarding Webhook, needs to be in Go High Level")
                    return jsonify({"status": "forwarded", "message": "Webhook forwarded successfully"}), 200
                else:
                    print("Failed to forward webhook")
                    return jsonify({"status": "error", "message": f"Failed to forward webhook. Status code: {response.status_code}"}), 500
            except requests.RequestException as e:
                print("Failed to forward")
                return jsonify({"status": "error", "message": f"Failed to forward webhook: {str(e)}"}), 500
        else:
            print("Webhook did not meet forwarding criteria")
            return jsonify({"status": "not forwarded", "message": "Webhook did not meet forwarding criteria"}), 200

def should_forward(transcript):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # or whichever model you prefer
            messages=[
                {"role": "system", "content": "You are an AI assistant that determines if a call transcript contains a request for scheduling an appointment or getting information about appointments."},
                {"role": "user", "content": f"""Analyze the following transcript and determine if the caller is requesting information about getting an appointment or wanting to schedule an appointment. 

Respond with 'Yes' ONLY if the transcript contains a clear request or inquiry about scheduling or getting information about an appointment. Otherwise, respond with 'No'.

Transcript: {transcript}

Remember, respond ONLY with 'Yes' or 'No'.
"""}
            ],
            max_tokens=3
        )
        decision = response.choices[0].message['content'].strip().lower()
        return decision == 'yes'
    except Exception as e:
        print(f"Error in should_forward: {str(e)}")
        return False  # Def
if __name__ == "__main__":
    app.run(debug=True)