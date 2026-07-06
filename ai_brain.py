import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    """로컬 AI에게 한글 단타 분석 의뢰"""
    system_instruction = (
        "너는 대한민국 최고의 주식 단타 전문가이다. 아래 규칙을 엄격히 지켜라.\n"
        "1. 모든 대답은 오직 '한국어'로만 한다. 영어는 단 한 단어도 섞지 마라.\n"
        '2. 출력은 반드시 JSON 규격만 허용한다: {"decision": "BUY/SELL/HOLD", "reason": "한글 상세 이유"}\n'
        "3. 가격 추세와 뉴스를 분석하여 1~3% 수익 확률이 높을 때만 BUY를 결정하라."
    )
    news_text = "\n".join(news_headlines) if news_headlines else "특이 뉴스 없음."
    user_message = f"종목: {ticker}, 가격: {current_price}원\n추세: {price_history_str}\n뉴스: {news_text}"

    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.1},
        )
        ai_reply = response.get("message", {}).get("content", "").strip()
        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"decision": "HOLD", "reason": "AI 응답 형식이 분석에 적합하지 않음."}
    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 분석 엔진 오류: {str(e)}"}
