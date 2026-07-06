# ai_brain.py
import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    """
    로컬 AI에게 현재 데이터와 뉴스를 주고 판단을 내리게 함 (100% 한글 보장)
    """
    system_instruction = (
        "너는 대한민국 최고의 주식 투자 전략가이다. 아래 규칙을 반드시 지켜라.\n"
        "1. 모든 답변은 반드시 '한국어'로만 작성한다. 영어를 단 한 단어도 쓰지 마라.\n"
        "2. 답변은 오직 JSON 형식으로만 출력한다.\n"
        '3. 형식: {"decision": "BUY/SELL/HOLD", "reason": "여기에 한글로 상세 이유 작성"}\n'
        "4. 'reason' 항목은 2문장 이상의 논리적인 한글로 작성하라."
    )

    news_context = (
        "\n".join(news_headlines) if news_headlines else "현재 수집된 특이 뉴스 없음"
    )
    user_message = (
        f"대상종목: {ticker}\n"
        f"현재가격: {current_price}원\n"
        f"최근추세: {price_history_str}\n"
        f"실시간뉴스: {news_context}\n"
        "위 데이터를 분석해서 한국어로만 결론을 내려줘."
    )

    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.2},
        )

        ai_reply = response.get("message", {}).get("content", "").strip()

        # JSON 추출용 정규표현식
        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            clean_json = json_match.group()
            return json.loads(clean_json)

        return {
            "decision": "HOLD",
            "reason": "AI가 비정상적인 응답을 반환하여 안전을 위해 관망합니다.",
        }

    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 분석 중 오류 발생: {str(e)}"}
