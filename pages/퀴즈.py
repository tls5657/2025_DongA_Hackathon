# streamlit_app/pages/1_퀴즈.py

import streamlit as st
from llm import generate_quiz

st.set_page_config(page_title="관련 퀴즈", page_icon="❓", layout="wide")

st.title("관련 퀴즈 풀기")

# 메인 페이지에서 넘어온 정보들
video_title = st.session_state.get("selected_video_title")
summary_text = st.session_state.get("quiz_source_summary", "")

# 세션 초기화
if "quiz_items" not in st.session_state:
    st.session_state.quiz_items = []

if "quiz_source_summary_snapshot" not in st.session_state:
    st.session_state.quiz_source_summary_snapshot = ""

if "quiz_correct_count" not in st.session_state:
    st.session_state.quiz_correct_count = 0

# 공통 스타일
st.markdown(
    """
    <style>
    /* 문제 카드 박스 */
    .question-card {
        padding: 1.4rem 1.6rem;
        border-radius: 0.9rem;
        border: 1px solid #e5e7eb;
        background-color: #f9fafb;
        margin-bottom: 1.8rem;
        box-shadow: 0 4px 10px rgba(15, 23, 42, 0.04);
    }

    /* 문제 텍스트 */
    .question-title {
        font-size: 1.1rem;
        line-height: 1.5;
        margin-bottom: 0.75rem;
    }

    .question-label {
        font-weight: 700;
        color: #2563eb; /* 파란색 */
        margin-right: 0.25rem;
    }

    /* 기본 선택지 버튼 (클릭 가능한 st.button) */
    div.stButton > button {
        border-radius: 10px;
        width: 100% !important;
        display: block;
        padding: 0.7rem 0.9rem;
        font-weight: 500;
        border: 1px solid #d1d5db;
        text-align: center;
        justify-content: center;
    }

    /* 선택 후 보여주는 고정 박스 버튼 */
    .option-pill {
        border-radius: 10px;
        padding: 0.7rem 0.9rem;
        font-weight: 500;
        width: 100%;
        border: none;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 상단 정보 표시
if video_title:
    st.info(f"현재 영상: {video_title}")
else:
    st.info("메인 페이지에서 영상을 선택한 후 들어오면 영상 제목이 표시됩니다.")

if not summary_text:
    st.markdown("---")
    st.warning("메인 페이지에서 AI 요약을 생성한 후 '퀴즈 풀기' 버튼을 눌러 들어와야 합니다.")
else:
    # 요약이 변경되면 새 퀴즈 생성
    if summary_text != st.session_state.quiz_source_summary_snapshot:
        with st.spinner("요약 내용을 기반으로 퀴즈를 생성하는 중입니다..."):
            quiz_items = generate_quiz(summary_text, num_questions=5)
            st.session_state.quiz_items = quiz_items
            st.session_state.quiz_source_summary_snapshot = summary_text

            # 기존 선택 상태 초기화
            for k in list(st.session_state.keys()):
                if "_selected" in k or "_is_correct" in k:
                    del st.session_state[k]

            st.session_state.quiz_correct_count = 0

    quiz_items = st.session_state.quiz_items

    if not quiz_items:
        st.markdown("---")
        st.error("퀴즈를 생성하지 못했습니다. 다시 시도해 주세요.")
    else:
        num_questions = len(quiz_items)

        # 현재까지 맞은 문제 수 계산
        correct = sum(
            1
            for idx in range(1, num_questions + 1)
            if st.session_state.get(f"q{idx}_is_correct")
        )
        st.session_state.quiz_correct_count = correct

        # 진행률 바
        st.progress(
            correct / num_questions,
            text=f"정답률: {correct}/{num_questions} 문제 정답",
        )

        st.markdown("---")

        # 문제 렌더링
        for idx, quiz in enumerate(quiz_items, start=1):
            question = quiz.get("question", "")
            options = quiz.get("options", [])
            answer_index = quiz.get("answer_index", 0)
            explanation = quiz.get("explanation", "")

            selected_key = f"q{idx}_selected"
            correct_key = f"q{idx}_is_correct"

            # 초기 상태 설정
            st.session_state.setdefault(selected_key, None)
            st.session_state.setdefault(correct_key, False)


            # 문제 텍스트 (문제 N. 부분 파란색 + bold, 전체 글자 크기 키움)
            st.markdown(
                f"""
                <p class="question-title">
                    <span class="question-label">문제 {idx}.</span>{question}
                </p>
                """,
                unsafe_allow_html=True,
            )

            # 보기 세로 배치
            if isinstance(options, list) and options:
                # 아직 선택 전: 실제 버튼
                if st.session_state[selected_key] is None:
                    for i, opt in enumerate(options):
                        label = f"{chr(65+i)}. {opt}"

                        if st.button(label, key=f"q{idx}_btn_{i}"):
                            st.session_state[selected_key] = i
                            st.session_state[correct_key] = (i == answer_index)
                            st.rerun()

                        # 보기 간 간격 작게
                        st.markdown(
                            "<div style='height:6px;'></div>", unsafe_allow_html=True
                        )
                else:
                    # 이미 선택된 후: 색상 고정 박스 렌더링
                    selected = st.session_state[selected_key]
                    is_correct = st.session_state[correct_key]

                    for i, opt in enumerate(options):
                        label = f"{chr(65+i)}. {opt}"

                        bg = "#e5e7eb"
                        color = "#111827"

                        if i == selected:
                            if is_correct:
                                bg = "#22c55e"  # 초록 (정답)
                                color = "#ffffff"
                            else:
                                bg = "#ef4444"  # 빨강 (오답)
                                color = "#ffffff"

                        pill_html = f"""
                        <button class="option-pill" style="background:{bg}; color:{color};">
                            {label}
                        </button>
                        """
                        st.markdown(pill_html, unsafe_allow_html=True)
                        st.markdown(
                            "<div style='height:6px;'></div>", unsafe_allow_html=True
                        )

            # 정답 및 해설
            with st.expander("정답 및 해설 보기"):
                if isinstance(options, list) and 0 <= answer_index < len(options):
                    st.markdown(
                        f"**정답:** {chr(65 + answer_index)}. {options[answer_index]}"
                    )
                else:
                    st.markdown("정답 정보를 제대로 불러오지 못했습니다.")

                if explanation:
                    st.markdown(f"**해설:** {explanation}")

            st.markdown("</div>", unsafe_allow_html=True)
