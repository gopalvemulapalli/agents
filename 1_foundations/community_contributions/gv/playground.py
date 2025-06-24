import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from IPython.display import Markdown, display

load_dotenv(override=True)

# String constants for model types
MODEL_TYPE_OPENAI = "openai"
MODEL_TYPE_GEMINI = "gemini"
MODEL_TYPE_CLAUDE = "claude"
MODEL_TYPE_DEEPSEEK = "deepseek"

# String constants for model names
MODEL_NAME_GPT_4O_MINI = "gpt-4o-mini"
MODEL_NAME_GEMINI_2_0_FLASH = "gemini-2.0-flash"
MODEL_NAME_CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20240620"
MODEL_NAME_DEEPSEEK_CHAT = "deepseek-chat"

available_llms = [MODEL_TYPE_OPENAI, MODEL_TYPE_GEMINI, MODEL_TYPE_CLAUDE, MODEL_TYPE_DEEPSEEK]

llms = [
    {"model_type": MODEL_TYPE_OPENAI, "model_name": MODEL_NAME_GPT_4O_MINI, "url": "https://api.openai.com/v1", "key": os.getenv("OPENAI_API_KEY")},
    {"model_type": MODEL_TYPE_GEMINI, "model_name": MODEL_NAME_GEMINI_2_0_FLASH, "url": "https://generativelanguage.googleapis.com/v1beta/openai/", "key": os.getenv("GEMINI_API_KEY")},
    {"model_type": MODEL_TYPE_CLAUDE, "model_name": MODEL_NAME_CLAUDE_3_5_SONNET, "url": "https://api.openai.com/v1", "key": os.getenv("CLAUDE_API_KEY")},
    {"model_type": MODEL_TYPE_DEEPSEEK, "model_name": MODEL_NAME_DEEPSEEK_CHAT, "url": "https://api.deepseek.com/v1", "key": os.getenv("DEEPSEEK_API_KEY")}
]


def get_llm_config_by_model_type(model_type):
    return next((llm for llm in llms if llm["model_type"] == model_type), None)


def get_client(llm):
    llm_config=get_llm_config_by_model_type(llm)
    if not llm_config:
        raise ValueError(f"Config not exist for {llm}.")
    if not llm_config["key"]:
        raise ValueError(f"API key for {llm_config['model_name']} is missing.")    
    if not llm_config["url"]:
        raise ValueError(f"URL for {llm_config['model_name']} is missing.")    
    if not llm_config["model_name"]:
        raise ValueError(f"Model name for {llm_config['model_type']} is missing.")

    return OpenAI(api_key=llm_config["key"], base_url=llm_config["url"]), llm_config["model_name"]

competitors = []
answers = []

bigQuestion="Who is at the fault in war between Iran and Israel?"
bigQuestion += "Should US be involved in the war?"

async def get_answer(llm_type, question)->str|None:
    message=[
        {"role":"user","content":question}
]

    try:
        print(f"Using {llm_type} as LLM.")
        
        clientInfo=get_client(llm_type)
        client,model=clientInfo[0], clientInfo[1]
        
        response= client.chat.completions.create(model=model, messages=message)

        answer=response.choices[0].message.content
        display(Markdown(answer),raw=True)

        return answer
    except Exception as e:
        print(f"Error: {e}")
        return None
import asyncio

# Call get_answer on all available LLMs in parallel
async def get_all_answers():
    tasks = [get_answer(llm_type, bigQuestion) for llm_type in available_llms]
    return await asyncio.gather(*tasks)

answers = []
competitors = []

loop = asyncio.get_event_loop()
results = loop.run_until_complete(get_all_answers())

for llm_type, answer in zip(available_llms, results):
    if answer:
        competitors.append(llm_type)
        answers.append(answer)

# for llm_type in available_llms:
#     answer=get_answer(llm_type,bigQuestion)
#     if answer:
#         competitors.append(llm_type)    
#         answers.append(answer)

together = ""
for index, answer in enumerate(answers):
    together += f"# Response from competitor {index+1}\n\n"
    together += f"{answer}\n\n"

#print(together)

judge = f"""You are judging a competition between {len(competitors)} competitors.
Each model has been given this question:

{bigQuestion}

Your job is to evaluate each response for clarity and strength of argument, and rank them in order of best to worst.
Respond with JSON, and only JSON, with the following format:
{{"results": ["best competitor number", "second best competitor number", "third best competitor number", ...]}}

Here are the responses from each competitor:

{together}

Now respond with the JSON with the ranked order of the competitors, nothing else. Do not include markdown formatting or code blocks."""

#print(judge)

results= asyncio.run(get_answer(MODEL_TYPE_GEMINI,judge))
print(results)

results_dict = json.loads(results)
ranks = results_dict["results"]
for index, result in enumerate(ranks):
    competitor = competitors[int(result)-1]
    print(f"Rank {index+1}: {competitor}")