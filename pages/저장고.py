# streamlit_app/pages/saved_video.py

import streamlit as st

st.set_page_config(page_title="저장한 영상", page_icon="🔖", layout="wide")

st.title("🔖 저장한 영상들")

# 세션 상태 기본값
if "saved_videos" not in st.session_state:
    st.session_state.saved_videos = []

if "selected_video" not in st.session_state:
    st.session_state.selected_video = None

if "selected_video_id" not in st.session_state:
    st.session_state.selected_video_id = None

if "video_transcript" not in st.session_state:
    st.session_state.video_transcript = None

saved_videos = st.session_state.saved_videos

if not saved_videos:
    st.info("아직 저장된 영상이 없습니다. 메인 화면에서 영상을 선택하고 '저장' 버튼을 눌러보세요.")
else:
    st.write(f"총 **{len(saved_videos)}개**의 영상이 저장되어 있습니다.")
    st.markdown("---")

    for idx, video in enumerate(saved_videos):
        with st.container():
            col_idx, col_thumb, col_info, col_delete = st.columns([0.2, 1, 3, 0.7])

            # 번호
            with col_idx:
                st.write(f"{idx + 1}")

            # 썸네일 (⚠️ Streamlit의 st.image는 직접 클릭 이벤트를 못 받아서
            #        바로 아래에 '이 영상 열기' 버튼을 두는 방식으로 구현할게)
            with col_thumb:
                if video.get("thumbnail"):
                    st.image(video["thumbnail"], width=80)

            # 제목 + "열기" 버튼
            with col_info:
                # 제목은 보기 좋게 텍스트로
                st.write(f"**{video['title']}**")
                st.caption(
                    f"채널: {video.get('channel_title', '알 수 없음')} • 조회수: {video['view_count']:,}회"
                )

                # 🔥 이 버튼을 누르면 app.py로 돌아가서
                #    선택한 영상으로 세팅 + 자막 다시 추출
                if st.button("▶ 이 영상 열기", key=f"open_{idx}"):
                    st.session_state.selected_video = video
                    st.session_state.selected_video_id = video["video_id"]
                    st.session_state.video_transcript = None  # 새 영상이니까 자막 다시 로드
                    st.switch_page("메인.py")

            # 삭제 버튼
            with col_delete:
                if st.button("🗑 삭제", key=f"delete_{idx}"):
                    st.session_state.saved_videos.pop(idx)
                    st.experimental_rerun()

        st.markdown("---")
