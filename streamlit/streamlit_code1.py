import streamlit as st
import openai
import re
from streamlit_chat import message

# 페이지 설정
st.set_page_config(page_title="Travel Planner Chatbot", layout="wide")

# Add custom CSS for styling (white theme)
st.markdown(
    """
    <style>
        body {
            background-color: #273346;
        }
        .title { font-size: 36px; font-weight: bold; color: #333333; }
        .subtitle { font-size: 24px; font-weight: bold; margin-top: 20px; color: #333333; }
        .bot-response, .user-response { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .bot-response { background-color: #f1f1f1; color: #333333; }
        .user-response { background-color: #e1f5fe; color: #0c5460; }
        .itinerary-content { margin-top: 10px; background-color: #fafafa; color: #333333; padding: 15px; border-radius: 8px; font-size: 16px; line-height: 1.6; }
    </style>
""",
    unsafe_allow_html=True,
)

# 제목과 설명
st.title("🌍 여행 계획 챗봇")
st.write(
    "이 챗봇은 개인 맞춤형 여행 일정을 제공합니다. "
    "다양한 목적지와 여행 기간을 선택하고 추가 정보를 입력해보세요."
)

# OpenAI API 키 입력
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("OpenAI API 키를 입력해주세요.", icon="🗝️")
else:
    openai.api_key = openai_api_key  # API 키 설정

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "destination" not in st.session_state:
    st.session_state.destination = None
if "stay_duration" not in st.session_state:
    st.session_state.stay_duration = None
if "companions" not in st.session_state:
    st.session_state.companions = []
if "companion" not in st.session_state:
    st.session_state.companion = None
if "itinerary_generated" not in st.session_state:
    st.session_state.itinerary_generated = False
if "itinerary" not in st.session_state:
    st.session_state.itinerary = ""

# 두 개의 열로 구성된 레이아웃 생성
col1, col2 = st.columns([1, 1])

with col1:

    # Assistant message for greeting
    message(
        "안녕하세요 여행자님! 여행자님의 계획 생성을 도와줄 리포입니다. 저와 함께 멋진 여행 일정을 만들어봐요! 그럼 질문에 맞는 답을 체크박스로 선택해주시면 바로 시작해볼게요!",
        is_user=False
    )

    # 도시 선택 체크박스 UI
    message("어느 도시를 여행하고 싶으신가요? 아래에서 도시를 선택해주세요.", is_user=False)
    cities = ["오사카", "파리", "방콕", "뉴욕"]

    for city in cities:
        if st.checkbox(
            city,
            key=f"city_{city}",
            disabled=st.session_state.destination is not None,
        ):
            st.session_state.destination = city

    # 선택된 도시 출력 (여행 기간 선택 체크박스 바로 위에 표시)
    if st.session_state.destination:
        message(f"{st.session_state.destination}로 여행을 가고 싶어!", is_user=True)
        message(f"{st.session_state.destination}로의 여행을 계획해드리겠습니다.", is_user=False)

    # 여행 기간 선택 체크박스 UI
    if st.session_state.destination:
        message(
            "언제 여행을 떠날 예정인가요? 여행 일자를 선택해주세요! 정확한 일자를 모르겠다면 'O박 O일' 형식으로 채팅을 남겨주세요",
            is_user=False
        )
        durations = ["1박 2일", "2박 3일", "3박 4일"]

        for duration in durations:
            if st.checkbox(
                duration,
                key=f"duration_{duration}",
                disabled=st.session_state.stay_duration is not None,
            ):
                st.session_state.stay_duration = duration

    if st.session_state.stay_duration:
        message(f"{st.session_state.stay_duration}만큼의 여행을 가고 싶어!", is_user=True)
        message(f"{st.session_state.stay_duration}의 기간만큼의 여행을 계획해드리겠습니다.", is_user=False)

    # 여행 동반자 선택 (하나만 선택 가능)
    if st.session_state.stay_duration:
        message("누구와 함께 여행을 떠나시나요? 하나만 선택해주세요.", is_user=False)
        companions = [
            "혼자", "친구와", "연인과", "가족과", "어린아이와", "반려동물과", "단체 여행"
        ]

        for companion in companions:
            if st.checkbox(
                companion,
                key=f"companion_{companion}",
                disabled=st.session_state.companion is not None,
            ):
                st.session_state.companion = companion

    if st.session_state.companion:
        message(f"이번 여행은 {st.session_state.companion}와 함께 떠나고 싶어!", is_user=True)
        message(f"{st.session_state.companion}와 함께하는 멋진 여행을 준비해드리겠습니다!", is_user=False)

    # 여행 일정 생성 조건: 도시, 기간, 동반자 모두 선택
    if (
        st.session_state.destination
        and st.session_state.stay_duration
        and st.session_state.companion
    ):
        if not st.session_state.itinerary_generated:
            try:
                with st.spinner("여행 일정을 생성하는 중입니다..."):
                    itinerary_request = (
                        f"{st.session_state.destination}로 {st.session_state.stay_duration} 동안 "
                        f"{st.session_state.companion}와 함께하는 여행 일정을 만들어 주세요. "
                        "각 날을 'Day 1:', 'Day 2:' 형식으로 나누고, 아침에는 특정 관광지와 아침 식사 장소를 추천해주시고, "
                        "점심에는 관광지와 점심 장소를 추천해주시고, 밤에는 야경 명소와 저녁 식사 장소를 추천해주세요. "
                        "각 문장은 한국어로 자연스럽게 작성해주세요."
                    )
                    response = openai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": itinerary_request}],
                    )
                    st.session_state.itinerary = response.choices[0].message.content
                    st.session_state.messages.append(
                        {"role": "assistant", "content": st.session_state.itinerary}
                    )
                    st.session_state.itinerary_generated = True

            except Exception as e:
                st.error(f"여행 일정 생성 중 오류가 발생했습니다: {e}")

    # 기존 메시지 출력
    for msg in st.session_state.messages:
        message(msg["content"], is_user=(msg["role"] == "user"))

# chat_input 처리
if prompt := st.chat_input("여행 기간을 입력하거나 질문해보세요."):
    if not (re.match(r"(\d+)박\s*(\d+)일", prompt) and st.session_state.stay_duration):
        st.session_state.messages.append({"role": "user", "content": prompt})

    # 일반 메시지 처리
    if st.session_state.messages:
        stream = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=st.session_state.messages,
            stream=True,
        )
        with col1:
            response = ""
            for chunk in stream:
                response += chunk["choices"][0]["delta"]["content"]
                message(response, is_user=False)
        st.session_state.messages.append({"role": "assistant", "content": response})

with col2:
    # Google 지도 표시
    if st.session_state.destination:
        st.subheader("🗺️ 여행 지도")
        map_url = f"https://www.google.com/maps/embed/v1/place?key=YOUR_GOOGLE_MAPS_API_KEY&q={st.session_state.destination}&zoom=12"
        st.markdown(
            f"""
            <iframe width="100%" height="400" frameborder="0" style="border:0" 
            src="{map_url}" allowfullscreen></iframe>
            """,
            unsafe_allow_html=True,
        )

    # 일정 표시
    if st.session_state.itinerary:
        st.subheader("🗺️ 여행 일정")
        itinerary_lines = st.session_state.itinerary.splitlines()
        days = [line for line in itinerary_lines if line.startswith("Day")]

        selected_day_content = ""
        if days:
            button_columns = st.columns(len(days))
            for i, day in enumerate(days):
                with button_columns[i]:
                    if st.button(day.strip(), key=f"button_{i}"):
                        start_index = itinerary_lines.index(day)
                        end_index = (
                            itinerary_lines.index(days[i + 1])
                            if i + 1 < len(days)
                            else len(itinerary_lines)
                        )
                        selected_day_content = "\n".join(
                            itinerary_lines[start_index:end_index]
                        )

            if selected_day_content:
                st.write("### 선택한 일정")
                st.markdown(selected_day_content.replace('\n', '<br>'), unsafe_allow_html=True)
        else:
            st.write("일정에 표시할 날짜가 없습니다. 전체 일정을 확인하세요:")
            st.write(st.session_state.itinerary)