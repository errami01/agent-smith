# Python `f.readlines()` Test Lab

This project provides a simple environment to test and understand how Python's `f.readlines()` function works, specifically focusing on how it handles memory, list structures, and trailing newline (`\n`) characters.

## 📁 1. Create a Test File
Before running the tests, create a file named `sample.txt` in the same directory as your Python script and add the following lines:

```text
Line 1: Hello World
Line 2: Testing f.readlines()
Line 3: Python is fun
```
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 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" \
  -d '{
  "model": "openai/gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
}'
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

uv run python -m student.agent_mbpp   --task-file test_mbpp_task.json   --output test_solution.json   --model-name "gemini-3.8-flash"   --provider-url "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"