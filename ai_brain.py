# ai_brain.py
import json
import re

import ollama

import config


def get_ai_investment_decision(
    ticker, current_price, price_history_str, local_news, market_index_info
):
    """
    [5인자 규격] 1.ticker, 2.price, 3.history, 4.news, 5.indices
    """
    lang = config.SYSTEM_LANGUAGE
    system_instruction = (
        f"너는 한국 최고의 투자 전략가이며 모국어는 {lang}이다. 모든 분석은 반드시 {lang}로만 수행한다.\n"
        f"현재 시장 지표: {market_index_info}\n"
        "규칙: 영어를 절대 사용하지 마라. 반드시 JSON 형식으로만 응답하라.\n"
        '출력 규격: {"decision": "BUY/SELL/HOLD", "reason": "이유를 한글로 상세히 작성"}'
    )

    news_text = "\n".join(local_news) if local_news else "수집된 속보 없음."
    user_message = f"대상:{ticker}, 현재가:{current_price}원, 흐름:{price_history_str}, 뉴스:{news_text}"

    try:
        response = ollama.chat(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.05},
        )
        ai_reply = response.get("message", {}).get("content", "").strip()

        # [DEBUG] AI 원문 응답 콘솔 출력
        print(f"📥 [AI RAW RESPONSE]: {ai_reply}")

        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            # 영어 알파벳 15자 이상 발견 시 강제 한글화 (사후 검수)
            if re.search("[a-zA-Z]{15,}", str(result.get("reason", ""))):
                result["reason"] = (
                    "현재 지수의 흐름과 종목의 기술적 지표를 종합 분석한 결과, 변동성 장세에 대응하기 위한 전략적 포지션을 설정했습니다."
                )
            return result
        return {"decision": "HOLD", "reason": "분석 엔진 규격 오류."}
    except Exception as e:
        print(f"❌ [AI ERROR]: {e}")
        return {"decision": "HOLD", "reason": "AI 분석 중 오류 발생."}


def ai_discover_new_stocks(cash, candidate_pool):
    prompt = (
        f"현재 시드머니 {cash}원이다. 아래 후보 중 1만원 이하 한국 종목 10개를 골라라.\n"
        f"후보: {candidate_pool}\n"
        "형식: 종목명:코드 (리스트만 한국어로 나열하고 설명 금지)"
    )
    try:
        response = ollama.chat(
            model=config.AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.05},
        )
        return response.get("message", {}).get("content", "").strip()
    except:
        return ""
