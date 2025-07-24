# 🤖 Why Every Programmer Is WRONG About AI Agents — The 6-Minute Proof

This repo contains two files that prove a powerful point:

> ⚠️ Most developers are still coding the hard way — while AI agents are doing the same tasks in minutes, with less code and more intelligence.

## 📂 What's Inside

### 1. `traditional.py`
A traditional Python CLI tool that uses the Google Calendar API to:

- Authenticate via OAuth
- Fetch events for a single day
- Insert new events manually
- Validate input manually (dates, timezones, emails)
- Handle edge cases with painful `if-else` logic

> 👨‍💻 Total dev time? Hours to days. Fragile. Not user-friendly.

---

### 2. `ai-agent.py`
A full agentic implementation using:

- 🧠 OpenAI's `gpt-4.1` model
- 🛠️ Function calling for Google Calendar integration
- 🔁 Recursive reasoning to retry on errors
- 🗣️ Natural language interface for event scheduling

> 💡 You can say:  
> _"Schedule a coffee chat next Friday at 2pm with Sarah and Mike."_  
> And it just works — no crashes, no formatting, no bugs.

---

## 🔍 Why This Matters

### 👎 The Old Way:
- Manual date/time parsing
- Regex validations
- Multiple CLI prompts
- Zero fault tolerance
- Limited feature scope

### 🚀 The Agent Way:
- Natural language input
- Automated parsing & validation
- Dynamic function calls
- Can add, fetch, update, or delete events
- Recovers from errors automatically
- Easily extensible with prompt updates

---

## 🧠 Powered By
- [OpenAI GPT-4.1](https://platform.openai.com/docs/guides/function-calling)
- [Google Calendar API](https://developers.google.com/calendar/api)
- [`loguru`](https://github.com/Delgan/loguru) for beautiful logging
- `google-auth`, `google-auth-oauthlib`, and `google-api-python-client`

---

## ⚙️ How to Run

### 🛠 Requirements
Install dependencies:

```bash
pip install -r requirements.txt
````

### 🔑 Setup

1. Create a [Google Cloud OAuth Project](https://console.cloud.google.com/apis/credentials)
2. Download your `credentials.json` and place it in the root of this repo
3. Add your OpenAI API key to the `OPENAI_API_KEY` variable inside `ai_calendar_agent.py`

---

### ▶️ Traditional CLI

```bash
python traditional.py
```

You'll be prompted to fetch or insert events using manual input.

---

### 🤖 AI Calendar Agent

```bash
python ai-agent.py
```

Then just type things like:

```text
What's on my calendar next Tuesday?
Schedule a call with Alice at 4pm EST tomorrow.
Delete my meeting with Bob on Friday.
```

And the agent will figure out the rest.

---

## 🧪 Real-World Metrics

> 205 OpenAI requests → 114,000 tokens
> 💸 Total Cost: \~\$0.28
> 🏎️ Time saved: hours, if not days

---

## 🧭 The Bigger Picture

This isn't just about calendar apps.

It's about **how software will be built** moving forward:

* You don't write endless logic.
* You describe what you want.
* The agent handles it.

Start prompt-engineering your future.
Stop hardcoding the past.

---

## 📽️ Watch the Breakdown

**→ Video: [Why Every Programmer Is WRONG About AI Agents (6-Minute Proof)](https://youtu.be/your-video-url)**
Get the full context, live demo, and insights on how this works.

---

## 💬 Feedback or Ideas?

Drop an issue, fork it, remix it — or just tell us:
**What do you want to build with AI agents next?**

---

*Keep prompting smart, not hard.*
