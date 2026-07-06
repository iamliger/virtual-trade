import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    system_instruction = (
        "너는 한국 최고의 소액 단타 전문가이다. "
        "모든 답변은 무조건 '한국어'로만 작성하라. 영어는 단 한 단어도 금지한다. "
        'JSON 형식만 출력: {"decision": "BUY/SELL/HOLD", "reason": "한글 이유"}'
    )
    news_text = "\n".join(news_headlines) if news_headlines else "뉴스 없음."
    user_message = f"종목:{ticker}, 현재가:{current_price}원, 흐름:{price_history_str}, 뉴스:{news_text}"

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
        return {"decision": "HOLD", "reason": "AI 분석 지연 중."}
    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 분석 에러: {str(e)}"}


def ai_discover_new_stocks(cash, candidate_pool):
    prompt = (
        f"현재 자본금은 {cash}원이다. 아래 [후보 리스트]에서 오늘 단타 수익이 유망한 "
        f"저가주 10개를 골라라. 반드시 한국어로 '종목명:코드' 형식으로만 나열하라.\n"
        f"[후보 리스트]: {candidate_pool}"
    )
    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        return response.get("message", {}).get("content", "").strip()
    except:
        return ""
