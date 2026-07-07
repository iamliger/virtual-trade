import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines, market_index_info
):
    system_instruction = (
        "너는 여의도 최고의 투자 전략가이다. 모든 분석은 반드시 한국어(Korean)로만 수행한다.\n"
        f"현재 시장 지표: {market_index_info}\n"
        "규칙:\n"
        "1. 영어를 단 한 단어라도 사용하지 마라.\n"
        "2. 반드시 JSON 형식으로만 응답하라.\n"
        '3. 출력 규격: {"decision": "BUY/SELL/HOLD", "reason": "이유를 한국어로 상세히 작성"}'
    )
    news_text = (
        "\n".join(news_headlines) if news_headlines else "현재 수집된 한국어 속보 없음."
    )
    user_message = f"대상:{ticker}, 현재가:{current_price}원, 흐름:{price_history_str}, 뉴스:{news_text}"

    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.05},
        )
        ai_reply = response.get("message", {}).get("content", "").strip()
        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            # 영어 다량 포함 시 강제 한글화 가드레일
            if re.search("[a-zA-Z]{15,}", result.get("reason", "")):
                result["reason"] = (
                    "시장 지표와 실시간 추세를 분석한 결과, 현재 지점에서의 변동성을 고려하여 전략적 매매 판단을 완료했습니다."
                )
            return result
        return {"decision": "HOLD", "reason": "분석 엔진 응답 지연."}
    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 분석 오류: {str(e)}"}


def ai_discover_new_stocks(cash, candidate_pool):
    prompt = (
        f"현재 자본금 {cash}원으로 살 수 있는 1만원 이하 한국 종목 10개를 골라라.\n"
        f"후보: {candidate_pool}\n"
        "출력형식: 종목명:코드 (리스트만 한국어로 나열)"
    )
    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.05},
        )
        return response.get("message", {}).get("content", "").strip()
    except:
        return ""
