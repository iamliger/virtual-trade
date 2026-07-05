# 🤖 로컬 AI 기반 가상 매매 시스템 프로젝트 매뉴얼 (무결점 가이드북)

본 문서는 주식을 전혀 모르는 초보 개발자나, 시간이 지나 다시 프로젝트를 열어본 관리자 모두가 단 5분 만에 환경을 이해하고 복구할 수 있도록 작성된 종합 참고서입니다.

---

## 1. 뼈대 요약 (이 프로젝트는 무엇인가?)
- **목적**: 돈을 쓰지 않고 내 컴퓨터의 로컬 AI(Ollama-Llama3)와 무료 주가 데이터(yfinance)를 엮어 작동하는 가상 주식 매매 프로그램을 만드는 것.
- **내 컴퓨터 주소**: `D:\ProjectWorkspace\AI\virtual-trade`
- **인터넷 백업 주소 (GitHub)**: `https://github.com/iamliger/virtual-trade`
- **내 깃허브 이메일**: `iamliger@nate.com`

---

## 2. 오랜만에 컴퓨터를 켰을 때 꼭 해야 하는 필수 명령어 (Git Bash 터미널)

컴퓨터를 새로 켜거나 VS Code를 다시 열면, 반드시 아래 2개의 명령어를 터미널에 쳐서 **가상환경**을 깨워야 합니다.

```bash
# ① 프로젝트 폴더로 정확하게 이동하기 (윈도우 D드라이브 기준)
cd /d/ProjectWorkspace/AI/virtual-trade

# ② 내 방 전용 파이썬 가상환경(venv) 활성화하기
source venv/Scripts/activate