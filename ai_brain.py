import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    """
    로컬 AI(Llama3)에게 한국어 전문가의 페르소나를 부여하여 판단 도출
    """
    system_instruction = (
        "너는 대한민국 최고의 주식 단타(Scalping) 전문가이다. 아래 규칙을 엄격히 지켜라.\n"
        "1. 모든 대답은 오직 '한국어'로만 한다. 영어는 단 한 단어도 섞지 마라.\n"
        "2. 출력은 반드시 아래 JSON 규격만 허용한다.\n"
        '{"decision": "BUY/SELL/HOLD", "reason": "여기에 한글로 상세 근거 작성"}\n'
        "3. 가격 추세와 뉴스를 종합하여 1~3% 수익을 낼 수 있는 타이밍을 포착하라."
    )

    news_text = (
        "\n".join(news_headlines) if news_headlines else "실시간 호재/악재 뉴스 없음."
    )
    user_message = (
        f"종목: {ticker}, 현재가: {current_price}원\n"
        f"최근 5분 흐름: {price_history_str}\n"
        f"수집된 뉴스: {news_text}\n"
        "위 데이터를 바탕으로 지금 매수, 매도, 관망 중 하나를 결정하고 한국어로 이유를 말해줘."
    )

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

        # 정규표현식으로 JSON만 추출하여 파싱 오류 방지
        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"decision": "HOLD", "reason": "AI 응답 형식 불일치로 인한 안전 관망."}
    except Exception as e:
        return {"decision": "HOLD", "reason": f"AI 분석 엔진 오류: {str(e)}"}
