# streamlit_app/app.py

import streamlit as st
from datetime import date
from io import BytesIO

from docx import Document
from utils.youtube_api2 import search_youtube_videos

# 🔥 유튜브 자막 추출용 라이브러리 & URL 파싱
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

# LLM 요약 모듈 (퀴즈는 퀴즈 페이지에서)
from llm import summarize_text


# -----------------------------------------------------------
# 기본 설정 & 전역 스타일(CSS)
# -----------------------------------------------------------
st.set_page_config(page_title="졸해 해커톤", page_icon="🎓", layout="wide")

if "saved_videos" not in st.session_state:
    st.session_state.saved_videos = []

st.markdown(
    """
    <style>
    /* 사이드바 검색 버튼: 파란색 테두리/텍스트 */
    div[data-testid="stSidebar"] div.stButton > button {
        border: 1px solid #1f6feb;
        color: #1f6feb;
    }
    div[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: rgba(31,111,235,0.1);
    }

    /* 퀴즈 버튼 스타일 (빨간색) */
    div[data-testid="quiz-button-container"] button {
        background-color: #ff4b4b !important;
        color: white !important;
    }
    div[data-testid="quiz-button-container"] button:hover {
        background-color: #e03a3a !important;
    }

    /* 🔥 오른쪽 패널 박스 테두리 스타일 */
    .right-panel-box {
        border: 1px solid #d0d7de;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
        background-color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------
# 유튜브 자막 추출용 함수들
# -----------------------------------------------------------

def extract_video_id(video_id_or_url: str) -> str:
    """
    유튜브 풀 URL이 오든, 순수 video_id가 오든
    항상 video_id만 뽑아서 반환.
    """
    s = video_id_or_url.strip()

    # youtu.be 단축 URL
    if "youtu.be" in s:
        parsed = urlparse(s)
        return parsed.path.lstrip("/")

    # youtube.com/watch?v= 형태
    if "youtube.com" in s:
        parsed = urlparse(s)
        qs = parse_qs(parsed.query)
        v = qs.get("v")
        if v and len(v) > 0:
            return v[0]

    # 그 외에는 이미 video_id라고 가정
    return s


def fetch_transcript(video_id_or_url: str, language: str = "ko") -> str:
    """
    유튜브 video_id 또는 URL + 언어코드로 자막 텍스트를 반환.
    """
    try:
        video_id = extract_video_id(video_id_or_url)

        api = YouTubeTranscriptApi()

        transcript_list = api.list(video_id)
        transcript = None

        # 지정 언어 우선
        try:
            transcript = transcript_list.find_transcript([language])
        except Exception:
            # 없으면 사용 가능한 첫 번째 자막
            transcript = next(iter(transcript_list))

        transcript_data = transcript.fetch()
        text_list = [entry.text for entry in transcript_data]

        full_text = " ".join(text_list)
        return f"[{transcript.language_code}] {full_text}"

    except Exception as e:
        return f"자막을 가져오는 중 오류 발생: {e}"


# -----------------------------------------------------------
# Session State 초기값 설정
# -----------------------------------------------------------
if "selected_video" not in st.session_state:
    st.session_state.selected_video = None

if "selected_video_id" not in st.session_state:
    st.session_state.selected_video_id = None

if "search_results" not in st.session_state:
    st.session_state.search_results = []

if "search_performed" not in st.session_state:
    st.session_state.search_performed = False

# AI 요약 결과
if "ai_summary" not in st.session_state:
    st.session_state.ai_summary = ""

# 공부 체크리스트 저장용
if "checklists" not in st.session_state:
    st.session_state.checklists = {}

# 학습 메모
if "study_memo" not in st.session_state:
    st.session_state.study_memo = ""

# 현재 선택한 영상의 자막 텍스트
if "video_transcript" not in st.session_state:
    st.session_state.video_transcript = None

# 퀴즈 페이지에 넘길 요약 텍스트
if "quiz_source_summary" not in st.session_state:
    st.session_state.quiz_source_summary = ""

# 퀴즈용 요약 스냅샷 (어떤 요약으로 퀴즈를 만들었는지 추적)
if "quiz_source_summary_snapshot" not in st.session_state:
    st.session_state.quiz_source_summary_snapshot = ""

# 퀴즈 페이지용: 선택한 영상 제목
if "selected_video_title" not in st.session_state:
    st.session_state.selected_video_title = None

DEFAULT_ROWS = 3  # 체크리스트 기본 행 수


# ===========================================================
# 1. 사이드바: 검색 & 결과 목록
# ===========================================================
with st.sidebar:
    # 검색어 입력 + 버튼 한 줄 배치 (라벨은 숨김)
    input_col, button_col = st.columns([3, 1])
    with input_col:
        search_query = st.text_input(
            label="검색어를 입력하세요 (유튜브)",
            label_visibility="collapsed",
            key="search_query",
            placeholder="검색어를 입력하세요 (유튜브)",
        )
    with button_col:
        search_button = st.button("검색", use_container_width=True)

    # 검색 실행
    if search_button and search_query.strip():
        with st.spinner("YouTube에서 영상을 불러오는 중..."):
            try:
                results = search_youtube_videos(search_query, max_results=10)
                st.session_state.search_results = results
                st.session_state.search_performed = True
                # 새 검색을 하면 선택 초기화
                st.session_state.selected_video = None
                st.session_state.selected_video_id = None
                st.session_state.video_transcript = None
                st.session_state.ai_summary = ""
                st.session_state.quiz_source_summary = ""
                st.session_state.selected_video_title = None
            except Exception as e:
                st.error(f"영상 검색 중 오류가 발생했습니다: {e}")
                st.session_state.search_results = []
                st.session_state.search_performed = True

    video_list = st.session_state.search_results

    st.markdown("---")
    st.subheader("검색 결과 (추천 순)")

    if video_list:

        def make_select_callback(i, vid):
            """체크박스를 클릭했을 때 호출되는 콜백."""
            def _cb():
                # 현재 선택 업데이트
                st.session_state.selected_video = vid
                st.session_state.selected_video_id = vid["video_id"]
                st.session_state.selected_video_title = vid["title"]

                # 새 영상 선택 시 상태 초기화
                st.session_state.video_transcript = None
                st.session_state.ai_summary = ""
                st.session_state.quiz_source_summary = ""

                # 다른 체크박스는 모두 False로 초기화
                for j in range(len(st.session_state.search_results)):
                    if j != i:
                        key = f"video_cb_{j}"
                        if key in st.session_state:
                            st.session_state[key] = False

            return _cb

        for idx, video in enumerate(video_list):
            with st.container():
                # 체크박스 + 썸네일 + 제목(조회수)
                check_col, thumb_col, info_col = st.columns([0.5, 1, 2.5])

                with check_col:
                    is_selected = (
                        video["video_id"] == st.session_state.selected_video_id
                    )
                    st.checkbox(
                        label="영상 선택",
                        key=f"video_cb_{idx}",
                        value=is_selected,
                        label_visibility="collapsed",
                        on_change=make_select_callback(idx, video),
                    )

                with thumb_col:
                    if video.get("thumbnail"):
                        st.image(
                            video["thumbnail"],
                            width=50,
                        )

                with info_col:
                    title_text = f"{video['title']} ({video['view_count']:,}회)"
                    st.write(title_text)

    else:
        if st.session_state.search_performed:
            st.write("검색 결과가 없습니다.")
        else:
            st.write("검색어를 입력하고 검색 버튼을 눌러 주세요.")


# ===========================================================
# 2. 메인 레이아웃: 왼쪽(영상/요약/퀴즈 버튼) + 오른쪽(메모/캘린더)
# ===========================================================
col_main, col_right = st.columns([2.3, 1])

# -----------------------------------------------------------
# 2-1. 왼쪽 영역: 영상 + AI 요약 + 퀴즈 버튼
# -----------------------------------------------------------
with col_main:
    st.markdown("### ☑️선택한 영상")

    video = st.session_state.selected_video

    if video:
        video_url = f"https://www.youtube.com/watch?v={video['video_id']}"

        # (1) 영상 플레이어
        st.video(video_url)

        # 자막 가져와서 세션에 저장
        if st.session_state.video_transcript is None:
            with st.spinner("자막 가져오는 중..."):
                transcript_text = fetch_transcript(video_url, language="ko")
                st.session_state.video_transcript = transcript_text

        # 제목 + 나중에 보기 버튼
        title_col, save_btn_col = st.columns([5, 1])
        with title_col:
            st.write(f"**제목:** {video['title']}")
            st.caption(
                f"채널: {video['channel_title']} • 조회수: {video['view_count']:,}회"
            )

        with save_btn_col:
            if st.button("🔖저장", key="save_for_later"):
                if video not in st.session_state.saved_videos:
                    st.session_state.saved_videos.append(video)
                    st.toast("저장되었습니다", icon="ℹ️")
                else:
                    st.toast("이미 저장된 영상입니다.", icon="⚠️")

        st.markdown("---")

        # (3) AI 내용 요약 공간
        if st.session_state.video_transcript is None:
            with st.spinner("자막 다시 가져오는 중..."):
                transcript = fetch_transcript(video_url)
                st.session_state.video_transcript = transcript

        if st.session_state.ai_summary == "" and st.session_state.video_transcript:
            with st.spinner("AI 요약 생성 중..."):
                summary = summarize_text(st.session_state.video_transcript)
                st.session_state.ai_summary = summary

        st.text_area(
            "AI 요약 결과",
            value=st.session_state.ai_summary,
            height=200
        )

        # (4) 퀴즈 풀기 버튼: 퀴즈 페이지로 이동
        quiz_btn_container = st.container()
        with quiz_btn_container:
            quiz_btn_container.markdown(
                '<div data-testid="quiz-button-container"></div>',
                unsafe_allow_html=True,
            )
            if st.button("퀴즈 풀기", key="quiz_button"):
                # 요약이 비어있으면 먼저 생성 시도
                if not st.session_state.ai_summary.strip():
                    if st.session_state.video_transcript:
                        with st.spinner("AI 요약 생성 중..."):
                            summary = summarize_text(st.session_state.video_transcript)
                            st.session_state.ai_summary = summary
                    else:
                        st.warning("자막을 먼저 불러온 뒤 요약을 생성해야 합니다.")
                # 퀴즈 페이지에 넘길 요약 저장
                if st.session_state.ai_summary.strip():
                    st.session_state.quiz_source_summary = st.session_state.ai_summary
                    # 페이지 이동
                    st.switch_page("pages/퀴즈.py")
                else:
                    st.warning("요약 생성에 실패했습니다. 다시 시도해 주세요.")

    

    else:
        st.write("사이드바에서 영상을 검색하고 선택하면 이 영역에 영상이 표시됩니다.")


# -----------------------------------------------------------
# 2-2. 오른쪽 영역: 학습 메모 + 공부 기록(캘린더 & 체크리스트)
# -----------------------------------------------------------
with col_right:
    # ------------------ 학습 메모 ------------------
    st.markdown('<div class="right-panel-box">', unsafe_allow_html=True)
    st.markdown("### 📝학습 메모")

    memo_text = st.text_area(
        "메모를 입력하세요",
        height=250,
        key="study_memo",
        placeholder="공부하면서 떠오르는 내용을 자유롭게 적어보세요.",
    )

    if memo_text.strip():
        # txt 저장
        txt_bytes = memo_text.encode("utf-8")
        st.download_button(
            label=".txt로 저장",
            data=txt_bytes,
            file_name="study_memo.txt",
            mime="text/plain",
            key="download_txt",
        )

        # docx 저장
        doc = Document()
        doc.add_paragraph(memo_text)
        doc_buffer = BytesIO()
        doc.save(doc_buffer)
        doc_buffer.seek(0)

        st.download_button(
            label=".doc로 저장",
            data=doc_buffer,
            file_name="study_memo.docx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            key="download_docx",
        )
    else:
        st.caption("메모를 입력하면 저장 버튼이 활성화됩니다.")


    # ------------------ 나의 공부 기록하기 ------------------
    st.markdown('<div class="right-panel-box">', unsafe_allow_html=True)
    st.markdown(
    '<h3 style="font-size:20px;">📍나의 공부 기록하기</h3>',
    unsafe_allow_html=True
    )
    st.write("공부 날짜를 선택하고, 그날의 공부 체크리스트를 작성해 보세요.")

    # 캘린더 (기본값: 오늘 날짜)
    selected_date = st.date_input(
        "공부 날짜 선택",
        value=date.today(),
        key="study_date",
    )
    selected_date_str = selected_date.isoformat()
    st.write(f"선택한 날짜: **{selected_date_str}**")

    # 날짜별 체크리스트 초기화
    if selected_date_str not in st.session_state.checklists:
        st.session_state.checklists[selected_date_str] = [
            {"text": "", "done": False} for _ in range(DEFAULT_ROWS)
        ]

    rows = st.session_state.checklists[selected_date_str]

    st.markdown("#### 오늘의 체크리스트")

    table_container = st.container()
    with table_container:
        for idx, row in enumerate(rows):
            task_key = f"{selected_date_str}_task_{idx}"
            done_key = f"{selected_date_str}_done_{idx}"

            if task_key not in st.session_state:
                st.session_state[task_key] = row["text"]
            if done_key not in st.session_state:
                st.session_state[done_key] = row["done"]

            task_col, done_col = st.columns([4, 2])
            with task_col:
                task_value = st.text_input(
                    label=f"할 일 {idx+1}",
                    value=st.session_state[task_key],
                    key=task_key,
                    label_visibility="collapsed",
                    placeholder="오늘 한 일 / 할 일을 입력하세요.",
                )
            with done_col:
                done_value = st.checkbox(
                    label="완료",
                    value=st.session_state[done_key],
                    key=done_key,
                )

            row["text"] = task_value
            row["done"] = done_value

        if st.button("+ 행 추가하기", key="add_row"):
            rows.append({"text": "", "done": False})

    if st.button("저장", key="save_checklist"):
        st.success(
            f"{selected_date_str}의 체크리스트가 저장되었습니다. "
            "다른 날짜를 눌렀다가 다시 돌아와도 내용은 유지됩니다."
        )
