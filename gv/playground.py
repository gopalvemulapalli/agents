import os
import google.generativeai as genai
import requests
import time

# Set up Gemini API key
GEMINI_API_KEY = os.environ["GOOGLE_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-pro")

# Set up Google Search API key and CX (Custom Search Engine ID)
GOOGLE_SEARCH_API_KEY = os.environ["GOOGLE_SEARCH_API_KEY"]
GOOGLE_SEARCH_CX = os.environ.get("GOOGLE_SEARCH_CX", "your_cx_id")  # Set your CX ID as env var or replace here

# 1. Plan searches with Gemini
def plan_searches(query, how_many=3):
    prompt = (
        f"You are a research planner. Given the query: '{query}', "
        f"list {how_many} specific web search queries to best answer it. "
        "Return as a Python list of strings."
    )
    response = gemini_model.generate_content(prompt)
    # Gemini may return code block formatting, so strip it if present
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("\n", 1)[0]
    try:
        queries = eval(text)
        if isinstance(queries, list):
            return queries
    except Exception:
        pass
    # Fallback: split by lines
    return [line.strip("- ") for line in text.splitlines() if line.strip()]

# 2. Google Search API

def google_search(query, num_results=5):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_SEARCH_API_KEY,
        "cx": GOOGLE_SEARCH_CX,
        "q": query,
        "num": num_results,
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"Google Search API error: {resp.text}")
        return []
    data = resp.json()
    results = []
    for item in data.get("items", []):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        link = item.get("link", "")
        results.append(f"{title}\n{snippet}\n{link}")
    return results

# 3. Synthesize report with Gemini
def synthesize_report(query, search_results):
    prompt = (
        f"You are a senior researcher. The original query is: '{query}'.\n"
        f"Here are the summarized search results for each sub-query, separated by --- lines:\n"
        f"{search_results}\n"
        "Write a detailed, well-structured report in markdown, at least 1000 words."
    )
    response = gemini_model.generate_content(prompt)
    return response.text

# 4. Full workflow
def deep_research(query):
    print(f"Planning searches for: {query}")
    search_plan = plan_searches(query)
    print(f"Search plan: {search_plan}")
    all_results = []
    for q in search_plan:
        print(f"Searching: {q}")
        results = google_search(q)
        all_results.append({"query": q, "results": results})
        time.sleep(1)  # To avoid hitting rate limits
    # Prepare summarized results
    summarized_results = "\n---\n".join(
        f"Search: {item['query']}\n" + "\n".join(item['results']) for item in all_results
    )
    print("Synthesizing report...")
    report = synthesize_report(query, summarized_results)
    print("\n===== FINAL REPORT =====\n")
    print(report)

if __name__ == "__main__":
    # Example usage
    research_query = "Latest AI Agent frameworks in 2025"
    deep_research(research_query)