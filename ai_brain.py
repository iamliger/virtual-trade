# ai_brain.py

import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    # 한글 전용 페르소나 주입 (영어를 쓸 경우 처벌하겠다는 수준의 강한 명령)
    system_instruction = (
        "너는 대한민국 최고의 전업 투자자이자 뉴스 분석가이다. "
        "모든 답변은 반드시 '한국어'로만 작성해야 한다. 영어를 섞지 마라. "
        "분석 이유(reason)에는 반드시 해당 뉴스가 주가에 미치는 영향을 포함해야 한다. "
        'JSON 형식만 출력하라: {"decision": "BUY/SELL/HOLD", "reason": "한국어로 작성된 상세 분석"}'
    )

    news_context = (
        "\n".join(news_headlines) if news_headlines else "현재 관련 뉴스 없음"
    )
    user_message = (
        f"종목: {ticker}, 현재가: {current_price}원, 추세: {price_history_str}\n"
        f"최신 뉴스:\n{news_context}\n"
        "이 데이터를 분석해서 오늘 단타 수익이 가능할지 판단해줘."
    )

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

        # JSON만 정교하게 추출 (정규표현식)
        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            # 키 이름이 영문이어도 값은 한글인지 재검증 (영어가 섞여있으면 강제 번역은 어려우니 재시도 권장)
            return result

        return {"decision": "HOLD", "reason": "AI 답변 형식 오류"}
    except Exception:
        return {"decision": "HOLD", "reason": "분석 엔진 일시 오류"}
