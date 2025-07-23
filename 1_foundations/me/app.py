from dotenv import load_dotenv
from gradio.components import textbox
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr



load_dotenv(override=True)

def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording {question}")
    return {"recorded": "ok"}

def write_to_log_file(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return {"written": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]


class Me:

    def __init__(self):
        self.openai = OpenAI()
        self.name = "Gopal Vemulapalli"

        #read linkedin
        reader = PdfReader("docs/linkedin.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text
        #read cv
        reader = PdfReader("docs/GV Updated CV.pdf")
        self.cv = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.cv += text
        #read summary
        with open("docs/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()


    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background, resume and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n ## Resume:\n{self.cv}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
    
    def chat(self, message, history):
        history = history or []
        history.append({"role": "user", "content": message})
        
        messages_for_api = [{"role": "system", "content": self.system_prompt()}] + history
        
        done = False
        while not done:
            response = self.openai.chat.completions.create(model="gpt-4o-mini", messages=messages_for_api, tools=tools)
            response_message = response.choices[0].message
            
            if response_message.tool_calls:
                messages_for_api.append(response_message)
                tool_calls = response_message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages_for_api.extend(results)
            else:
                done = True
        
        history.append(response_message.model_dump())
        
        chatbot_display = self.format_for_chatbot(history)
        
        return chatbot_display, history

    def format_for_chatbot(self, history):
        if not history:
            return []
        
        chatbot_messages = []
        user_message_content = None

        for msg in history:
            if msg["role"] == "user":
                user_message_content = msg["content"]
            elif msg["role"] == "assistant" and msg.get("content") is not None:
                if user_message_content:
                    chatbot_messages.append([user_message_content, msg["content"]])
                    user_message_content = None

        return chatbot_messages

    @staticmethod
    def clear():
        return None, "", []
           # Example interactions
examples = [
    ["Tell me about your self"],
    ["Your contact details"],
    ["How many years of experience do you have in .Net"],
    ["Do you have any experience with React?"],
    ["Send me your CV"]
]


if __name__ == "__main__":
    me = Me()

with gr.Blocks(css="#header-label { min-height: 100px; font-size: 1.5em; }") as demo:
    header = gr.Label("Profile Chat - Gopal Vemulapalli", label="")
    chatbot = gr.Chatbot(label="Chat History")
    history = gr.State([])  # Add a State to store chat history
    
    with gr.Row():
        input_text = gr.Textbox(placeholder="Enter your text here",label="Your query")
        submit_btn = gr.Button("Submit")
        reset_btn = gr.Button("Reset")
    # Examples as buttons
    gr.Examples(
        examples=examples,
        inputs=input_text,
        label="Try these examples:"
    )
    
    submit_btn.click(me.chat, inputs=[input_text, history], outputs=[chatbot, history])
    reset_btn.click(Me.clear,inputs=None, outputs=[chatbot, input_text, history])

    demo.launch()

    # iface = gr.ChatInterface(
    #     me.chat,
       
    #     #textbox = gr.Textbox(placeholder="Ask anything about me!",container=False),
    #     title="Chat with Gopal Vemulapalli",
    #     description="Chatbot to answer queries regarding Gopal Vemulapalli skills, experiences",
    #     examples=examples
    #     #theme="rich"
    # )
    # iface.launch()
    