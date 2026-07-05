# ai_brain.py

import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    system_instruction = (
        "너는 대한민국 최고의 주식 투자 전문가이다. "
        "모든 답변은 반드시 '한국어'로만 작성하라. 영어는 절대 쓰지 마라. "
        "응답은 반드시 아래 JSON 형식만 허용한다. "
        '{"decision": "BUY/SELL/HOLD", "reason": "여기에 한글로 상세 이유 작성"}'
    )

    news_context = "\n".join(news_headlines) if news_headlines else "특이 뉴스 없음"
    user_message = f"종목:{ticker}, 가격:{current_price}, 추세:{price_history_str}, 뉴스:{news_context}"

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
            return json.loads(json_match.group())
        return {"decision": "HOLD", "reason": "AI 응답 형식 오류 (관망)"}
    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 에러: {str(e)}"}
