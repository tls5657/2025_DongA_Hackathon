# kanana.py (Colab에서 실행되는 실제 LLM 추론 모듈)

import json
from llama_cpp import Llama

# ================================================================
# 1) 모델 로드 (Colab에서 처음에 1번만 실행됨)
# ================================================================
MODEL_PATH = r"C:\Users\user\Desktop\JH\kanana-1.5-2.1b-instruct-2505-Q4_K_M.gguf"

print("모델 로딩 중...")
model = Llama(
    model_path=MODEL_PATH,
    n_ctx=8192,
    n_gpu_layers=0,
    n_batch=512,
    verbose=False,
    # 필요하면 chat_format 지정 가능 (모델 포맷에 따라 조정)
    # chat_format="chatml",
)
print("LLM 모델 로딩 완료!")


# ================================================================
# 2) 프롬프트 템플릿
# ================================================================
SYSTEM_PROMPT_SUMMARY = (
    "You are a professional assistant skilled at summarizing long texts "
    "clearly and concisely."
)

SYSTEM_PROMPT_QUIZ = (
    "You are an AI tutor that creates high-quality multiple-choice quiz "
    "questions in Korean, based on the given study summary. "
    "You must always respond in valid JSON only."
)


def format_summary_prompt(script_content: str) -> str:
    user_request = f"""
다음은 사용자가 제공한 텍스트입니다.
---
[텍스트 본문]
{script_content}
---
[요청]
위 텍스트 본문의 핵심 주제와 주요 내용을 3줄로 간결하게 요약해 주고 난이도를 알려주세요.
"""
    return f"<system>{SYSTEM_PROMPT_SUMMARY}</system><user>{user_request}</user><assistant>"


def format_quiz_user_prompt(summary_content: str, num_questions: int = 5) -> str:
    # response_format으로 JSON Schema를 강제하므로,
    # 여기서는 "이런 구조로 만들어라" 정도만 설명해도 충분.
    return f"""
다음은 어떤 강의/영상의 요약 내용입니다.
---
[요약 본문]
{summary_content}
---
[요청]
위 요약 내용을 바탕으로 한국어로 {num_questions}개의 객관식 퀴즈를 만들어 주세요.

각 퀴즈는:
- 하나의 개념/포인트를 명확히 묻는 문제
- 보기 4개를 가지는 객관식
- 정답은 보기 중 하나
- 간단한 해설 포함

반드시 시스템이 지정한 JSON Schema 형식에 맞춰서만 출력하세요.
"""


# ================================================================
# 3) 외부에서 호출하는 요약 함수
# ================================================================
def summarize_text(text: str) -> str:
    """Streamlit에서 transcript 문자열을 받아 요약 생성"""

    prompt = format_summary_prompt(text)

    output = model(
        prompt=prompt,
        max_tokens=500,
        temperature=0.2,
        top_p=0.9,
        stop=["<", "user>", "system>"],
    )

    result = output["choices"][0]["text"].strip()
    return result


# ================================================================
# 4) 외부에서 호출하는 퀴즈 생성 함수 (JSON Schema 강제)
# ================================================================
def generate_quiz(summary_text: str, num_questions: int = 5):
    """
    요약 텍스트를 받아 퀴즈 리스트를 JSON 형태로 반환.

    스키마 (최상위):

    {
      "quizzes": [
        {
          "question": "문제 내용",
          "options": ["보기1", "보기2", "보기3", "보기4"],
          "answer_index": 0,
          "explanation": "정답 이유"
        },
        ...
      ]
    }

    반환은 quizzes 리스트만 반환:
    [
      { ... },
      ...
    ]
    """

    # JSON Schema 정의
    quiz_schema = {
        "type": "object",
        "properties": {
            "quizzes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 4,
                            "maxItems": 4,
                        },
                        "answer_index": {"type": "integer"},
                        "explanation": {"type": "string"},
                    },
                    "required": [
                        "question",
                        "options",
                        "answer_index",
                        "explanation",
                    ],
                },
                "minItems": 1,
            }
        },
        "required": ["quizzes"],
    }

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT_QUIZ,
        },
        {
            "role": "user",
            "content": format_quiz_user_prompt(summary_text, num_questions),
        },
    ]

    response = model.create_chat_completion(
        messages=messages,
        temperature=0.4,
        top_p=0.9,
        max_tokens=1024,
        response_format={
            "type": "json_object",
            "schema": quiz_schema,
        },
    )

    content = response["choices"][0]["message"]["content"]

    try:
        data = json.loads(content)
        quizzes = data.get("quizzes", [])
        # 최소한의 형식 검증
        if isinstance(quizzes, list):
            return quizzes
        return []
    except Exception:
        # 만약 JSON 파싱 실패하면 빈 리스트 반환
        return []
