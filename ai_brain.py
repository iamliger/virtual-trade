# ai_brain.py

import json
import re  # 복잡한 문자열에서 JSON만 추출하기 위한 도구

import ollama


def get_ai_investment_decision(
    ticker, current_price, price_history_str, news_headlines
):
    # 1. AI에게 더 강력하게 명령 (가스라이팅 수준)
    system_instruction = (
        "You are a professional stock trader. "
        "Analyze the data and respond ONLY with a valid JSON object. "
        "No talk, no apology, no intro. ONLY JSON. "
        'Format: {"decision": "BUY/SELL/HOLD", "reason": "한글 이유"}'
    )

    news_context = (
        "\n".join(news_headlines) if news_headlines else "현재 관련 뉴스 없음"
    )
    user_message = f"Stock: {ticker}, Price: {current_price}, Trend: {price_history_str}, News: {news_context}"

    print(f"\n--- [디버깅] AI 분석 시작: {ticker} ---")
    print(f"📡 [송신 데이터]: {user_message[:100]}...")  # 데이터가 잘 가는지 확인

    try:
        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.1},  # 0.1로 낮춰서 더 기계적으로 답변하게 함
        )

        ai_reply = response.get("message", {}).get("content", "").strip()

        # 🔥 [콘솔 출력] AI가 실제로 한 말을 터미널에서 직접 확인하세요!
        print(f"📥 [AI 원문 응답]:\n{ai_reply}")
        print("------------------------------------------")

        # 2. JSON 추출 로직 강화 (정규표현식 사용)
        json_match = re.search(r"\{.*\}", ai_reply, re.DOTALL)
        if json_match:
            clean_json = json_match.group()
            result = json.loads(clean_json)
            return result
        else:
            print("❌ [디버깅] AI 응답에서 JSON 형식을 찾을 수 없습니다.")
            return {"decision": "HOLD", "reason": "AI 응답 형식 오류 (콘솔 확인 필요)"}

    except Exception as e:
        print(f"🚨 [디버깅] AI 처리 중 에러 발생: {e}")
        return {"decision": "HOLD", "reason": f"시스템 에러: {str(e)[:30]}"}
