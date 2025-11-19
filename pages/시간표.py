# streamlit_app/pages/3_timetable.py

import json
from pathlib import Path

import streamlit as st
from utils.youtube_api import search_youtube_videos


# ---------------- Session state 초기값 ----------------
if "tt_panel_open" not in st.session_state:
    st.session_state.tt_panel_open = False
if "tt_panel_info" not in st.session_state:
    st.session_state.tt_panel_info = {}

# app.py 쪽에서 사용하는 상태값이 없으면 기본값 넣어두기
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "search_performed" not in st.session_state:
    st.session_state.search_performed = False
if "selected_video" not in st.session_state:
    st.session_state.selected_video = None
if "selected_video_id" not in st.session_state:
    st.session_state.selected_video_id = None
if "video_transcript" not in st.session_state:
    st.session_state.video_transcript = None

# ---------------- 시간표 기본 데이터 ----------------
DAYS = ["월", "화", "수", "목", "금"]
PERIODS = [1, 2, 3, 4, 5, 6, 7]

# 과목별 이모지 (같은 과목 = 같은 색 이모지)
SUBJECT_EMOJI = {
    "대학수학": "🟦",
    "물리 및 실험": "🟧",
    "정보검색": "🟨",
    "지식재산개론": "🟥",
    "자기이해와봉사": "🟩",
    "실증적AI개발프로젝트I": "🟪",
    "뉴럴네트워크": "🟫",
    "임베디드시스템": "⬛",
    "자연언어처리": "⬜",
    "빅데이터분석": "🟩",
    "실증적AI개발프로젝트II": "🟪",
}

# 각 학기별 시간표 (예시는 너가 쓰던 것 그대로 유지)
TIMETABLES = {
    "2025년 1학기": [
        {"subject": "대학수학", "day": "화", "period": 2, "room": "S06-0603"},
        {"subject": "대학수학", "day": "화", "period": 3, "room": "S06-0603"},
        {"subject": "정보검색", "day": "목", "period": 3, "room": "S06-0602"},
        {"subject": "지식재산개론", "day": "금", "period": 3, "room": "S06-0604"},
        {"subject": "물리 및 실험", "day": "월", "period": 5, "room": "S06-0606"},
        {"subject": "물리 및 실험", "day": "수", "period": 5, "room": "S06-0606"},
        {"subject": "정보검색", "day": "월", "period": 6, "room": "S06-0602"},
        {"subject": "자기이해와봉사", "day": "목", "period": 6, "room": "S01-0603"},
        {"subject": "실증적AI개발프로젝트I", "day": "금", "period": 7, "room": "S06-0602"},
    ],
    "2025년 2학기": [
        {"subject": "뉴럴네트워크", "day": "목", "period": 2, "room": "S06-0606"},
        {"subject": "임베디드시스템", "day": "금", "period": 2, "room": "S06-0603"},
        {"subject": "임베디드시스템", "day": "금", "period": 3, "room": "S06-0603"},
        {"subject": "자연언어처리", "day": "수", "period": 3, "room": "S06-0603"},
        {"subject": "자연언어처리", "day": "목", "period": 4, "room": "S06-0603"},
        {"subject": "빅데이터분석", "day": "수", "period": 5, "room": "S06-0609"},
        {"subject": "빅데이터분석", "day": "목", "period": 5, "room": "S06-0609"},
        {"subject": "뉴럴네트워크", "day": "월", "period": 5, "room": "S06-0606"},
        {"subject": "실증적AI개발프로젝트II", "day": "금", "period": 7, "room": "S06-0602"},
    ],
}


def build_grid(semester_key: str):
    """(day, period) -> item 매핑 생성"""
    grid = {(day, p): None for day in DAYS for p in PERIODS}
    for item in TIMETABLES.get(semester_key, []):
        grid[(item["day"], item["period"])] = item
    return grid


# ---------------- 강의계획서(json) 로드 ----------------
HERE = Path(__file__).resolve().parent  # 3_timetable.py가 있는 폴더

def load_json(filename: str):
    path = HERE / filename
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# math = 대학수학, money = 지식재산개론, mooli = 물리 및 실험
MATH_PLAN = load_json("math.json")
MONEY_PLAN = load_json("money.json")
MOOLI_PLAN = load_json("mooli.json")

SYLLABUS_MAP = {
    "대학수학": MATH_PLAN,
    "지식재산개론": MONEY_PLAN,
    "물리 및 실험": MOOLI_PLAN,
}


# ---------------- CSS (시간표 전용 스타일) ----------------
css = """
<style>
/* 시간표 전체 래퍼 */
.tt-grid {
    margin-top: 1rem;
}

/* 컬럼 안쪽 여백 줄이기 (칸 사이 간격 최소화) */
.tt-grid [data-testid="column"] {
    padding-left: 1px;
    padding-right: 1px;
}

/* 세로 블록 간 gap 줄이기 (윗/아랫 간격 제거) */
.tt-grid [data-testid="stVerticalBlock"] {
    gap: 0;
}

/* 헤더(요일, 교시) 공통 스타일 */
.tt-header {
    border: 1px solid #999999;
    min-height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #fafafa;
    font-weight: 600;
}

/* 빈 칸 */
.tt-cell-empty {
    height: 80px;
    border: 1px dashed #cccccc;   /* 점선 */
    background-color: #ffffff;
}

/* 과목 칸 안의 버튼 스타일 */
.tt-grid div[data-testid="stButton"] {
    width: 100%;
}

.tt-grid div[data-testid="stButton"] > button {
    width: 100%;
    height: 80px;                 /* 모든 셀 동일 높이 */
    border-radius: 0;             /* 네모 모서리 직각 */
    border: 1px solid #999999;    /* 칸 테두리 */
    background-color: #ffffff;    /* 흰 배경 */
    box-shadow: none !important;  /* 그림자 제거 */
    font-size: 0.8rem;
    line-height: 1.3;
    white-space: normal;          /* 줄바꿈 허용 */
    text-align: center;
    padding: 4px 6px;
}

.tt-grid div[data-testid="stButton"] > button:hover {
    background-color: #f3f3f3 !important;
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------- 상단: 제목 + 드롭다운 + 버튼 ----------------
st.markdown("### 시간표")

top_left, top_spacer, top_right = st.columns([2, 4, 2])

with top_left:
    semester = st.selectbox(
        "시간표 선택",
        ["2025년 1학기", "2025년 2학기"],
        index=0,
        key="tt_semester",
    )

with top_spacer:
    st.write("")

with top_right:
    if st.button("시간표 추가하기", key="add_timetable", use_container_width=True):
        st.toast("시간표 추가 기능은 추후 구현될 예정입니다.", icon="ℹ️")

st.markdown("---")

# ---------------- 선택한 학기의 시간표 렌더링 ----------------
grid = build_grid(semester)

st.write(f"#### {semester} 시간표")

st.markdown('<div class="tt-grid">', unsafe_allow_html=True)

# 헤더 (요일)
header_cols = st.columns(len(DAYS) + 1)
with header_cols[0]:
    st.markdown('<div class="tt-header"></div>', unsafe_allow_html=True)
for i, day in enumerate(DAYS):
    with header_cols[i + 1]:
        st.markdown(
            f'<div class="tt-header">{day}</div>',
            unsafe_allow_html=True,
        )

# 각 교시별 행
for period in PERIODS:
    row_cols = st.columns(len(DAYS) + 1)

    # 첫 번째 열: 교시 번호
    with row_cols[0]:
        st.markdown(
            f'<div class="tt-header">{period}교시</div>',
            unsafe_allow_html=True,
        )

    # 요일별 칸
    for j, day in enumerate(DAYS):
        cell = grid.get((day, period))
        col = row_cols[j + 1]

        with col:
            if cell is None:
                # 빈 칸
                st.markdown(
                    '<div class="tt-cell-empty"></div>',
                    unsafe_allow_html=True,
                )
            else:
                subj = cell["subject"]
                room = cell["room"]
                emoji = SUBJECT_EMOJI.get(subj, "⬜️")
                label = f"{emoji} {subj}\n{room}"

                if st.button(
                    label,
                    key=f"tt_{semester}_{day}_{period}",
                ):
                    st.session_state.tt_panel_info = {
                        "semester": semester,
                        "subject": subj,
                        "day": day,
                        "period": period,
                        "room": room,
                    }
                    st.session_state.tt_panel_open = True

st.markdown("</div>", unsafe_allow_html=True)

# ---------------- 과목 클릭 시: 아래쪽 정보 패널 ----------------
if st.session_state.tt_panel_open and st.session_state.tt_panel_info:
    info = st.session_state.tt_panel_info
    st.markdown("---")
    st.markdown("### 선택한 과목 정보")

    box = st.container(border=True)
    with box:
        subject = info["subject"]

        st.write(f"**과목명:** {subject}")
        st.write(f"**학기:** {info['semester']}")
        st.write(f"**요일 / 교시:** {info['day']}요일 {info['period']}교시")
        st.write(f"**강의실:** {info['room']}")

        # ===== 15주차 강의계획서 → app.py 검색 연동 =====
        if subject in SYLLABUS_MAP and SYLLABUS_MAP[subject]:
            syllabus = SYLLABUS_MAP[subject]

            st.markdown("#### 15주차 강의 계획")

            # '1주', '2주', ..., '15주' 형식의 키만 뽑아서 정렬
            week_keys = [k for k in syllabus.keys() if k.endswith("주")]
            week_keys.sort(key=lambda x: int(x.replace("주", "")))

            for wk in week_keys:
                week_data = syllabus[wk]
                goal = (week_data.get("학습목표") or "").replace("\n", " ")
                content = (week_data.get("학습내용") or "").replace("\n", " ")

                # 내용이 완전 비어 있으면 버튼 안 만들기
                if not goal and not content:
                    continue

                btn_label = f"{wk} | {goal}" if goal else f"{wk} | {content}"

                if st.button(btn_label, key=f"{subject}_{wk}"):
                    # 검색어: 과목명 + 주차 + 학습내용/목표
                    query = f"{subject} {wk} {content or goal}"

                    st.session_state.search_query = query
                    try:
                        results = search_youtube_videos(query, max_results=10)
                        st.session_state.search_results = results
                        st.session_state.search_performed = True
                        st.session_state.selected_video = None
                        st.session_state.selected_video_id = None
                        st.session_state.video_transcript = None
                    except Exception as e:
                        st.error(f"영상 검색 중 오류가 발생했습니다: {e}")
                    else:
                        # app.py로 이동해서, 거기서 영상 선택/자막/퀴즈까지 이어지게 함
                        st.switch_page("메인.py")
        else:
            st.info(
                "이 과목에 연결된 강의계획서(15주차)가 아직 없거나, json 파일을 찾지 못했습니다."
            )

        # 패널 닫기
        if st.button("창 닫기", key="close_tt_panel"):
            st.session_state.tt_panel_open = False
