# Lab 1: LLM Course-Planning Agent

Start with **Agentic_AI_Lab1.pdf** for the task requirements,
grading, report questions and submission instructions.

- Release date: 2026/10/28
- Due date: 2026/11/11; use the closing time shown on eeclass.

Complete this lab on the **course server** using the Python environment and shared model service provided by the teaching team. This package contains fictional course data, student profiles and setup examples. You must implement Q1, Q2, Q3 and the three-model comparison yourself.

This lab emphasizes observing and explaining LLM behavior. Model outputs are not required to satisfy every constraint. The improved prompt and repair process are not guaranteed to
produce better results.

Grades are based on your implementation, experimental procedure, complete records and evidence-based explanations, not model success rate. Your validator must still check the required
constraints correctly, and your program must never report success for a schedule rejected by the validator.

## Package layout

```text
Agentic_AI_Lab1.pdf
Agentic_AI_Lab1/
  README.md
  data/
    courses.csv
    profiles.json
  schemas/
    schedule_schema.json
  starter/
    data_utils.py
  examples/
    minimal_api_example.py
    inspect_data.py
    schedule_example.json
```

Keep the directory structure inside `Agentic_AI_Lab1/` unchanged. The supplied helper locates `data/` relative to the project root.

You may work using Python scripts or a Jupyter notebook. Follow the corresponding instructions below.

## 1. Use the course environment

Use the shared Python environment provided by the teaching team. Do not install, upgrade or remove packages, create additional Python environments, or modify the shared environment.

Do not start model servers or download model weights.

### For Python scripts

In a JupyterLab Terminal, activate the shared environment:

```bash
source /opt/biic-classroom/lab1-venv/bin/activate
```

Check the provided packages:

```bash
python -c "import openai, dotenv, pytest, jsonschema; print('Environment OK')"
```

Change to the project folder before running the examples. If you extracted it into your home directory, run:

```bash
cd ~/Agentic_AI_Lab1
```

### For Jupyter notebooks

Select the course kernel installed by the teaching team. Activating the environment in a Terminal does not change a notebook's kernel.

Run this cell:

```python
import sys
print(sys.executable)

import openai
import dotenv
import pytest
import jsonschema

print("Environment OK")
```

The Python path should be:

```text
/opt/biic-classroom/lab1-venv/bin/python
```

Create or open your notebook directly inside the `Agentic_AI_Lab1/` folder. Check its working directory:

```python
from pathlib import Path

print(Path.cwd())
```

The displayed directory should be your `Agentic_AI_Lab1/` project folder.

## 2. Check the provided data

This check loads the catalog, profiles and output schema without calling a model.

### From a Terminal

Run from the project root after activating the course environment:

```bash
python examples/inspect_data.py
```

### From a Jupyter notebook

Run this cell from a notebook whose working directory is the project root:

```python
%run examples/inspect_data.py
```

Either method should report **28 courses and 8 profiles**, followed by the available fields and the first two catalog rows.

If a file cannot be found, check your working directory and confirm that the package directory structure has been preserved.

## 3. Check the shared model service

The course server provides a shared OpenAI-compatible API backed by vLLM. The teaching team configures the API environment variables automatically when your JupyterHub server starts. You do not need to export them manually or create a `.env` file.

All available models use the same API base URL:

```text
http://127.0.0.1:8000/v1
```

| API model name | Actual model |
|---|---|
| `qwen2.5:3b` | `Qwen/Qwen2.5-3B-Instruct` |
| `qwen2.5:7b` | `Qwen/Qwen2.5-7B-Instruct` |
| `llama3.1:8b` | `meta-llama/Llama-3.1-8B-Instruct` |

Choose one primary model for Q1–Q3. Use all three models for the three-model comparison.

### Test from a Terminal

Run these commands from the project root after activating the shared Python environment:

```bash
python examples/minimal_api_example.py --model qwen2.5:3b
python examples/minimal_api_example.py --model qwen2.5:7b
python examples/minimal_api_example.py --model llama3.1:8b
```

Each command should print the selected model and a response containing `API works`.

### Test from a Jupyter notebook

After confirming that you selected the course kernel, run this cell:

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.getenv("LLM_API_KEY", "classroom-internal"),
    timeout=float(os.getenv("LLM_TIMEOUT", "120")),
    max_retries=0,
)

models = ["qwen2.5:3b", "qwen2.5:7b", "llama3.1:8b"]

for model in models:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with exactly: API works"},
            ],
            temperature=0,
            max_tokens=32,
            stream=False,
        )
        print(f"{model}: {response.choices[0].message.content}")
    except Exception as exc:
        print(f"{model}: API call failed ({type(exc).__name__}).")
        print("Check the selected kernel, API base URL and model name.")
        print("If the request timed out, wait briefly and try again.")
```

Each model should return a response containing `API works`.


### Settings for your implementation

Use the same API base URL and select the model through the request's `model` field. Use non-streaming requests (`stream=False`).

Each deployed model has a context limit of **4096 tokens**, including both input and generated output. Keep prompts, conversation history and the requested output length within this limit. The connectivity example uses `max_tokens=32` because it requests only a short reply; choose an appropriate output limit for your course-planning tasks.

Record the API model name, actual model and generation settings in your experiment logs. Do not include API keys or authentication tokens.

If a call fails, check the activated Python environment or selected notebook kernel, API base URL and model name. If it times out, wait briefly and try again.

Record API failures separately. Do not count a connection failure as an invalid course schedule or a completed model-response latency measurement.

## 4. Read the data rules before implementing

- `courses.csv` is the authoritative catalog. The supplied loader converts `credits` and `recommended_year` to integers.
- The literal `None` means no prerequisite. Semicolon-separated prerequisites must **all** have been completed before this semester. Selecting a prerequisite in the proposed schedule does not count as completing it. Do not assume equivalence between different course IDs.
- Use the selected profile's `completed_courses`, `min_credits`, `max_credits` and `required_courses`. A catalog course marked `type=required` is not automatically mandatory in this particular semester.
- `recommended_year`, department match, interests and difficulty are recommendation preferences, not additional hard enrollment rules.
- `earliest_start` and `blocked_periods` are available time preferences. Choose at least one additional hard constraint for Q2 and record which rules are activated. Any time restriction explicitly stated as mandatory in a request must be enforced. Q3's Friday-afternoon-free constraint must be active in the infeasible test, even if you selected another extra constraint for Q2.
- Days are `Mon`, `Tue`, `Wed`, `Thu` or `Fri`; times use 24-hour `HH:MM`. Each catalog row has one class meeting. Adjacent intervals do not overlap. In this lab, Friday afternoon means `Fri 12:00–23:59`.
- A profile describes a fictional student, not the student submitting the assignment. You may use any provided profile; record its ID and any request-specific requirements. Keep the supplied catalog and profiles unchanged for graded experiments.

## 5. Output structure and experiment logs

`schemas/schedule_schema.json` is a formal JSON Schema (Draft 2020-12) for the model's proposed schedule. `examples/schedule_example.json` illustrates the output structure; it is **not** a guaranteed valid complete schedule for a provided profile.

Schema validity does not establish course validity. Catalog membership, prerequisites, completed courses, credits, required courses and time restrictions still require deterministic Python checks.

Create these four result files:

```text
results/q1_conversation.json
results/q2_experiments.json
results/q3_history.json
results/q2_model_comparison.json
```

For reproducibility, record the following:

| File | Required evidence |
|---|---|
| `q1_conversation.json` | Model/settings and ordered conversation messages, including each message's `role` and `content` and the system instructions. |
| `q2_experiments.json` | Complete baseline and improved prompts, model/settings, profile and active constraints, raw responses and validation results for each run. |
| `q3_history.json` | Original case inputs, model/settings, attempt limit, every attempt's messages, raw response, validation results and final status. Include the feedback sent during repair. |
| `q2_model_comparison.json` | Inputs, prompts, settings, raw responses, elapsed seconds and validation results for all three models. |

Each result file must be valid JSON. Store malformed model output as a string such as `raw_response`, with the parsing error in its validation record. Preserve the original responses; do not manually correct them before validation. Use run/case IDs so your report can refer to the recorded evidence.

Preserve failed outputs and unsuccessful repair attempts. You are not required to rerun experiments until they succeed.

If you use a student-constructed invalid test case for a report question, label it clearly and keep it separate from the original model responses.

## 6. Write your report

Write **`Lab1_StudentID_report.pdf`**, replacing `StudentID` with your student ID. Include:

- Your name, student ID and primary model.
- Answers to Q1.1–Q1.3, Q2.1–Q2.4 and Q3.1–Q3.4.
- The three-model comparison table and answers to its two questions.
- Run/case IDs supporting your excerpts and comparisons.
- Explain observed errors and limitations using recorded outputs
  and validator messages. For repairs, discuss which errors were
  fixed, repeated or newly introduced.

All required report questions are in `Agentic_AI_Lab1.pdf`.
## 7. Submit

Submit **`Lab1_StudentID.zip`** containing one top-level folder **`Lab1_StudentID/`**, replacing `StudentID` with your student ID.

For example:

```text
Lab1_115000001.zip
  Lab1_115000001/
    ...
    Lab1_115000001_report.pdf
```

Include your Python scripts or notebook, all four result logs, the report and any supporting modules needed to run your work.
