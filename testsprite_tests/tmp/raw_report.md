
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** nusatrade
- **Date:** 2025-12-09
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001
- **Test Name:** post api v1 ai generate strategy
- **Test Code:** [TC001_post_api_v1_ai_generate_strategy.py](./TC001_post_api_v1_ai_generate_strategy.py)
- **Test Error:** Traceback (most recent call last):
  File "<string>", line 16, in authenticate
  File "/var/task/requests/models.py", line 1024, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 422 Client Error: Unprocessable Entity for url: http://localhost:8000/api/v1/auth/login

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 62, in <module>
  File "<string>", line 24, in test_post_api_v1_ai_generate_strategy
  File "<string>", line 21, in authenticate
Exception: Authentication failed: 422 Client Error: Unprocessable Entity for url: http://localhost:8000/api/v1/auth/login

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8a19eff0-bced-4a6f-abb8-76d1f40b9cd7/1957ecf8-cb4b-432d-a769-869a875a022f
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002
- **Test Name:** post api v1 backtest run
- **Test Code:** [TC002_post_api_v1_backtest_run.py](./TC002_post_api_v1_backtest_run.py)
- **Test Error:** Traceback (most recent call last):
  File "<string>", line 17, in login_and_get_token
  File "/var/task/requests/models.py", line 1024, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 422 Client Error: Unprocessable Entity for url: http://localhost:8000/api/v1/auth/login

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 116, in <module>
  File "<string>", line 64, in test_post_api_v1_backtest_run
  File "<string>", line 22, in login_and_get_token
RuntimeError: Login request failed: 422 Client Error: Unprocessable Entity for url: http://localhost:8000/api/v1/auth/login

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8a19eff0-bced-4a6f-abb8-76d1f40b9cd7/3020891e-e73a-49d8-923b-9802c77fc4f7
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC007
- **Test Name:** get api v1 ml models
- **Test Code:** [TC007_get_api_v1_ml_models.py](./TC007_get_api_v1_ml_models.py)
- **Test Error:** Traceback (most recent call last):
  File "<string>", line 16, in authenticate
  File "/var/task/requests/models.py", line 1024, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 422 Client Error: Unprocessable Entity for url: http://localhost:8000/api/v1/auth/login

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 59, in <module>
  File "<string>", line 29, in test_get_api_v1_ml_models
  File "<string>", line 26, in authenticate
RuntimeError: Authentication failed: 422 Client Error: Unprocessable Entity for url: http://localhost:8000/api/v1/auth/login

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8a19eff0-bced-4a6f-abb8-76d1f40b9cd7/3fe3f5e6-6012-4066-a9d6-3c4c147f70e4
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC008
- **Test Name:** post api v1 ml models
- **Test Code:** [TC008_post_api_v1_ml_models.py](./TC008_post_api_v1_ml_models.py)
- **Test Error:** Traceback (most recent call last):
  File "<string>", line 17, in get_jwt_token
  File "/var/task/requests/models.py", line 1024, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 422 Client Error: Unprocessable Entity for url: http://localhost:8000/api/v1/auth/login

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 90, in <module>
  File "<string>", line 29, in test_post_api_v1_ml_models
  File "<string>", line 23, in get_jwt_token
AssertionError: Login request failed: 422 Client Error: Unprocessable Entity for url: http://localhost:8000/api/v1/auth/login

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8a19eff0-bced-4a6f-abb8-76d1f40b9cd7/1a860303-eb99-43a1-91a6-594152dff727
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC010
- **Test Name:** post api v1 ai chat
- **Test Code:** [TC010_post_api_v1_ai_chat.py](./TC010_post_api_v1_ai_chat.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 62, in <module>
  File "<string>", line 21, in test_post_api_v1_ai_chat
AssertionError: Login failed: {"detail":"Incorrect email or password. 4 attempts remaining."}

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8a19eff0-bced-4a6f-abb8-76d1f40b9cd7/6f5d0a4a-615b-4e9a-984d-6beb4558b408
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **0.00** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---