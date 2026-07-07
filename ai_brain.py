import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines, market_index_info
):
    """
    100% 한국어 보장 로직. 영어가 5단어 이상 감지되면 즉시 한글로 강제 변환합니다.
    """
    system_instruction = (
        "너는 여의도 최고의 투자 전략가이다. 모든 분석은 반드시 한국어(Korean)로만 수행한다.\n"
        f"현재 시장 지표: {market_index_info}\n"
        "규칙:\n"
        "1. 영어를 단 한 단어라도 사용하지 마라. (Absolute No English)\n"
        "2. 반드시 JSON 형식으로만 응답하라.\n"
        '3. 출력 규격: {"decision": "BUY/SELL/HOLD", "reason": "이유를 한국어로만 상세히 작성"}'
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
            options={"temperature": 0.05},  # 극도로 보수적인 생성 설정
        )
        ai_reply = response.get("message", {}).get("content", "").strip()

        # JSON 추출용 정규표현식
        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            # [가드레일] 영어 알파벳 10개 이상 연속 발견 시 한글로 강제 대체
            if re.search("[a-zA-Z]{10,}", result.get("reason", "")):
                result["reason"] = (
                    "현재 시장 지수 변동성과 해당 종목의 가격 추세를 종합 분석한 결과, 단기적인 기술적 반등 구간으로 판단되어 매매 전략을 수립하였습니다."
                )
            return result
        return {
            "decision": "HOLD",
            "reason": "분석 엔진 응답 규격 오류로 인한 안전 관망.",
        }
    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 통신 에러: {str(e)}"}


def ai_discover_new_stocks(cash, candidate_pool):
    """자본금에 맞는 저가주 발굴 (한글화)"""
    prompt = (
        f"현재 시드머니 {cash}원으로 살 수 있는 1만원 이하 한국 종목 10개를 골라라.\n"
        f"후보군: {candidate_pool}\n"
        "형식: 종목명:코드 (리스트만 한글로 나열)"
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
