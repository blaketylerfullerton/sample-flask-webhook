from flask import Flask, request, jsonify
import openai
import os


openai.api_key = os.getenv('OPENAI_API_KEY')
# Set up Airtable
AIRTABLE_BASE_KEY = os.getenv('AIRTABLE_BASE_KEY')
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME')
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')

AIRTABLE_URL = f"https://api.airtable.com/v0/appONw8OOzv9YX4yT/Call%20Logs"

from flask import render_template

app = Flask(__name__)

@app.route("/")
def hello_world():
    return render_template("index.html")

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        data = request.json
         # Check if the event is 'call_ended'
        if data.get('event') != 'call_ended':
            return jsonify({"status": "success", "message": "Event ignored"}), 200
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
            # Extract the summary from the OpenAI response
            summary = response.choices[0].message['content']
            # You can now store or process the summary as needed
            print("Call Summary:", summary)
            # Optionally, you can add the summary to the response
            data['call']['summary'] = summary

             # Calculate durations
            start_time = datetime.fromtimestamp(call_data['start_timestamp'] / 1000)
            end_time = datetime.fromtimestamp(call_data['end_timestamp'] / 1000)
            duration = end_time - start_time
            duration_str = f"{duration.seconds // 60}m {duration.seconds % 60}s"
            

            # Prepare data for Airtable
            airtable_data = {
                "records": [
                    {
                        "fields": {
                            "Date": start_time.isoformat(),
                            "Duration AI": duration_str,
                            "Duration": duration_str,
                            "Summary": summary,
                            "Transcript": transcript,
                            "Recording": [{"url": call_data.get('recording_url', '')}],
                            "Number": call_data.get('from_number', ''),
                            "End Reason": call_data.get('disconnection_reason', ''),
                            "Call SID": call_data.get('metadata', {}).get('twilio_call_sid', ''),
                            "Start Timestamp": str(call_data['start_timestamp'])
                        }
                    }
                ]
            }
              # Send data to Airtable
            headers = {
                "Authorization": f"Bearer {AIRTABLE_API_KEY}",
                "Content-Type": "application/json"
            }
            airtable_response = requests.post(AIRTABLE_URL, json=airtable_data, headers=headers)
            if airtable_response.status_code == 200:
                print("Data successfully sent to Airtable")
            else:
                print(f"Failed to send data to Airtable. Status code: {airtable_response.status_code}")
                print(f"Response: {airtable_response.text}")

            return jsonify({"status": "success", "data": data}), 200
        except Exception as e:
            print(f"Error in OpenAI API call: {str(e)}")
            return jsonify({"status": "error", "message": "Failed to generate summary"}), 500
    else:
        return jsonify({"status": "error", "message": "Method not allowed"}), 405

if __name__ == "__main__":
    app.run(debug=True)