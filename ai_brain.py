import json
import re

import ollama

import config


def get_ai_investment_decision(
    ticker, current_price, price_history_str, global_news, local_news, market_index_info
):
    """
    config.SYSTEM_LANGUAGE를 기반으로 한 절대 언어 고정 로직
    """
    lang = config.SYSTEM_LANGUAGE
    system_instruction = (
        f"너는 여의도 최고의 투자 전략가이며, 너의 모국어는 {lang}이다. 모든 대답은 반드시 {lang}로만 한다.\n"
        f"현재 시장 지표: {market_index_info}\n"
        f"규칙: 영어를 한 단어도 섞지 마라. 반드시 JSON 형식으로 {lang}로만 응답하라.\n"
        '출력 규격: {"decision": "BUY/SELL/HOLD", "reason": "이유를 한글로 상세히 작성"}'
    )

    news_text = "\n".join(local_news) if local_news else "속보 없음."
    user_message = f"대상:{ticker}, 현재가:{current_price}원, 흐름:{price_history_str}, 뉴스:{news_text}"

    try:
        response = ollama.chat(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": config.AI_TEMPERATURE},
        )
        ai_reply = response.get("message", {}).get("content", "").strip()

        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            # 영어 알파벳이 15자 이상 발견되면 강제 한글화 (사후 검수)
            if re.search("[a-zA-Z]{15,}", str(result.get("reason", ""))):
                result["reason"] = (
                    f"현재 시장의 흐름과 {ticker}의 수급 상황을 종합 분석한 결과, 기술적 지표에 따른 {result['decision']} 전략을 추천합니다."
                )
            return result
        return {
            "decision": "HOLD",
            "reason": "분석 엔진이 응답 규격을 준수하지 않아 관망합니다.",
        }
    except Exception:
        return {"decision": "HOLD", "reason": "AI 엔진과의 통신이 원활하지 않습니다."}


def ai_discover_new_stocks(cash, candidate_pool):
    prompt = (
        f"현재 시드머니 {cash}원으로 살 수 있는 1만원 이하 한국 종목 10개를 골라라.\n"
        f"후보: {candidate_pool}\n"
        f"반드시 {config.SYSTEM_LANGUAGE}로 '종목명:코드' 형식으로만 나열하고 설명은 금지한다."
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
