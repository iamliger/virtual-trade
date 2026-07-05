# ai_brain.py

import json
import re

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    # 1. 시스템 프롬프트를 한국어 전문가답게 대개편
    system_instruction = (
        "You are a 'Scalping Master' in the Korean Stock Market. "
        "Your goal is to make a small profit (1-3%) within a short time. "
        "Analyze the price trend and news headlines very aggressively. "
        "If the news is positive and the price is rising, DECIDE BUY. "
        "If there's any sign of a drop, DECIDE SELL or HOLD. "
        "Your reason must be in Korean and explain WHY this is good for SCALPING."
    )

    news_context = (
        "\n".join(news_headlines)
        if news_headlines
        else "호재나 악재 뉴스가 현재 없습니다."
    )
    user_message = (
        f"종목: {ticker}\n"
        f"현재가: {current_price}원\n"
        f"최근 추세: {price_history_str}\n"
        f"관련 뉴스: {news_context}\n"
        "위 데이터를 바탕으로 분석 결과를 JSON으로만 출력하세요."
    )

    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.2},  # 0.2로 낮춰서 더 정확하고 일관된 답변을 유도
        )

        ai_reply = response.get("message", {}).get("content", "").strip()
        print(f"📥 [AI 원문 응답]:\n{ai_reply}")

        # JSON만 추출 (정규표현식)
        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            clean_json = json_match.group()
            result = json.loads(clean_json)

            # 💡 [보강] AI가 키 이름을 잘못 썼을 경우를 대비한 방어 코드
            final_decision = (
                result.get("decision") or result.get("recommendation") or "HOLD"
            )
            final_reason = result.get("reason", "분석 내용을 생성하지 못했습니다.")

            return {"decision": final_decision, "reason": final_reason}

        return {"decision": "HOLD", "reason": "AI 답변 형식 오류로 인한 대기"}

    except Exception as e:
        return {"decision": "HOLD", "reason": f"분석 엔진 오류: {str(e)}"}
