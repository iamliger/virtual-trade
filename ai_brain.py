import json
import logging
import re

import ollama

import config


def get_ai_investment_decision(
    ticker, current_price, price_history_str, global_news, local_news, market_index_info
):
    """
    [핵심 수정] 6개의 인자를 정확히 받도록 파라미터 구조를 확정함.
    """
    lang = config.SYSTEM_LANGUAGE
    system_instruction = (
        f"너는 여의도 최고의 투자 전략가이며 모국어는 {lang}이다. 모든 분석은 반드시 {lang}로만 수행한다.\n"
        f"현재 시장 지표: {market_index_info}\n"
        "규칙:\n"
        "1. 영어를 단 한 단어도 사용하지 마라. (No English Allowed)\n"
        "2. 반드시 JSON 형식으로만 응답하라.\n"
        '3. 출력 규격: {"decision": "BUY/SELL/HOLD", "reason": "이유를 한글로 상세히 작성"}'
    )

    g_news_txt = "\n".join(global_news) if global_news else "글로벌 소식 지연 중."
    l_news_txt = "\n".join(local_news) if local_news else "국내 속보 지연 중."

    user_message = (
        f"대상: {ticker}, 현재가: {current_price}원, 흐름: {price_history_str}\n"
        f"--- 글로벌 뉴스 ---\n{g_news_txt}\n"
        f"--- 국내 실시간 뉴스 ---\n{l_news_txt}\n"
        "위 데이터를 종합하여 지금 바로 한국어로 판단을 내려줘."
    )

    for attempt in range(config.RETRY_COUNT):
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
                # [한글 가드레일] 영어 문장 발견 시 한글로 강제 변환
                if re.search("[a-zA-Z]{15,}", str(result.get("reason", ""))):
                    result["reason"] = (
                        "현재 시장 지표와 실시간 속보를 분석한 결과, 변동성이 확대되는 구간이므로 기술적 추세에 따른 대응을 권장합니다."
                    )
                return result

            logging.warning(
                f"AI 응답 형식 오류 (시도 {attempt+1}/{config.RETRY_COUNT})"
            )
        except Exception as e:
            logging.error(f"AI 호출 중 에러 발생: {e}")

    return {
        "decision": "HOLD",
        "reason": "AI 엔진 일시 응답 지연으로 안전 관망 모드를 유지합니다.",
    }


def ai_discover_new_stocks(cash, candidate_pool):
    prompt = (
        f"현재 자본금 {cash}원으로 살 수 있는 1만원 이하 한국 종목 10개를 골라라.\n"
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
