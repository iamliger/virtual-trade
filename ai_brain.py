import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, global_news, local_news, market_index_info
):
    """
    글로벌(Yahoo)과 로컬(Naver) 뉴스를 모두 분석하여 판단을 내리는 100% 한글 엔진
    """
    system_instruction = (
        "너는 여의도 최고의 투자 전략가이다. 모든 분석은 반드시 한국어(Korean)로만 수행한다.\n"
        f"현재 시장 지표: {market_index_info}\n"
        "규칙:\n"
        "1. 영어를 단 한 단어라도 사용하지 마라.\n"
        "2. 반드시 JSON 형식으로만 응답하라.\n"
        '3. 출력 규격: {"decision": "BUY/SELL/HOLD", "reason": "이유를 한국어로 상세히 작성"}'
    )

    g_news_txt = "\n".join(global_news) if global_news else "글로벌 소식 없음."
    l_news_txt = "\n".join(local_news) if local_news else "국내 속보 없음."

    user_message = (
        f"대상: {ticker}, 현재가: {current_price}원, 흐름: {price_history_str}\n"
        f"--- 글로벌 뉴스 ---\n{g_news_txt}\n"
        f"--- 국내 실시간 뉴스 ---\n{l_news_txt}\n"
        "위 데이터를 종합하여 지금 바로 한국어로 판단을 내려줘."
    )

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
            # 영어 섞임 방지 가드레일
            if re.search("[a-zA-Z]{15,}", result.get("reason", "")):
                result["reason"] = (
                    "글로벌 뉴스 및 국내 속보를 분석한 결과, 현재 지수의 변동성을 고려하여 기술적 분석에 기반한 매매 전략을 유지합니다."
                )
            return result
        return {"decision": "HOLD", "reason": "분석 엔진 규격 오류 발생."}
    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 분석 에러: {str(e)}"}


def ai_discover_new_stocks(cash, candidate_pool):
    prompt = (
        f"자본금 {cash}원으로 살 수 있는 1만원 이하 한국 종목 10개를 골라라.\n"
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
