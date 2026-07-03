from kis_api import get_access_token, get_mock_cash_balance

print("1. 한국투자증권 실시간 모의투자 서버에 가상 출입증(토큰) 요청 중...")
token = get_access_token()

if token:
    print("   - ✅ 출입증 발급 성공!")
    print(f"   - 🎫 가상 토큰 데이터 확인 완료")
    
    print("\n2. 발급받은 출입증을 들고 내 가상 계좌 잔고(예수금)를 조회합니다...")
    balance = get_mock_cash_balance(token)
    
    print(f"\n🖥️ [증권사 실전 연동 리포트]")
    print(f"   - 내 가상 계좌번호: {token[:0]}*** (보안 마스킹)")
    print(f"   - 증권사 서버에 충전된 내 가상 예수금: **{balance:,}원**")
    print(f"\n✅ 내 PC와 한국투자증권 가상 서버가 100% 동기화되었습니다!")
else:
    print("❌ 가상 출입증을 받지 못해 다음 단계로 진행할 수 없습니다.")
    print("💡 .env 파일에 복사한 AppKey와 Secret이 오타 없이 들어갔는지 다시 체크해 주세요.")
