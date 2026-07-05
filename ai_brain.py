# ai_brain.py

import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    # 영어 사용을 절대 금지하는 시스템 프롬프트
    system_instruction = (
        "너는 한국의 20년 경력 수석 주식 분석가이다. "
        "모든 답변은 반드시 '한국어'로만 작성해야 하며, 영어는 단 한 단어도 사용하지 마라. "
        "응답은 반드시 아래 JSON 형식만 허용한다. "
        '{"decision": "BUY/SELL/HOLD", "reason": "여기에 한국어로만 상세 분석 내용 작성"}'
    )

    # 뉴스가 없을 때를 위한 보충
    news_content = (
        "\n".join(news_headlines)
        if news_headlines
        else "현재 실시간 뉴스는 없으나 차트 추세가 매우 중요함."
    )

    user_message = (
        f"종목명: {ticker}\n현재가격: {current_price}원\n최근추세: {price_history_str}\n"
        f"수집된뉴스: {news_content}\n"
        "이 데이터를 분석해서 오늘 단타 수익이 가능한지 한국어로만 알려줘."
    )

    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.1},  # 낮을수록 일관성 있고 헛소리를 안 함
        )
        ai_reply = response.get("message", {}).get("content", "").strip()

        # JSON만 추출
        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"decision": "HOLD", "reason": "분석 엔진 응답 지연으로 안전 관망 유지."}
    except Exception:
        return {"decision": "HOLD", "reason": "AI 브레인 일시 오류로 안전 관망 유지."}
