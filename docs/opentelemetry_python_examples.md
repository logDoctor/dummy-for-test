# Python 코드로 보는 OpenTelemetry 3대 핵심 기둥
앞서 비유로 설명해 드린 **Trace(트레이스), Metric(메트릭), Log(로그)**가 실제 파이썬 코드로는 어떻게 구현되고 작동하는지 직관적으로 정리해 보았습니다.

---

## 1. Trace (트레이스) - 흐름 추적 🕵️‍♂️
**목적:** 코드가 실행되는 구간별 묶음(Span)을 만들고, 각 구간이 얼마나 오래 걸렸는지, 어떤 특징이 있는지 발자취를 남깁니다.

```python
from opentelemetry import trace
import time

# Tracer 객체 가져오기
tracer = trace.get_tracer("my-python-app")

def order_steak():
    # 1. '주문 받기'라는 가장 큰 틀의 상위 Span을 시작합니다.
    with tracer.start_as_current_span("Process_Order_Request") as parent_span:
        parent_span.set_attribute("Customer_Level", "VIP") # 5W1H 속성 추가
        
        # 2. 그 속에서 '고기 굽기'라는 하위 단계 Span을 엽니다.
        with tracer.start_as_current_span("Cook_Steak") as child_span:
            child_span.set_attribute("steak_type", "Medium Rare")
            
            # 실제 요리(비즈니스 로직) 시작
            print("고기를 굽습니다...")
            time.sleep(2) # 2초 소요 가정
```
**설명:** 이렇게 코드를 `with tracer.start_as_current_span("...")` 블록으로 감싸주기만 하면, 각 작업 단위가 시작되고 끝날 때 걸린 시간이 자동 측정되어 모니터링 화면(Azure)에 블록 형태의 타임라인으로 그려집니다.

---

## 2. Metric (메트릭) - 수치 압축 📊
**목적:** 하나하나의 사건을 기록하는 것이 아니라, 누적된 카운트나 평균값 같은 숫자를 수집합니다.

```python
from opentelemetry import metrics

# Meter 객체 가져오기
meter = metrics.get_meter("my-python-app")

# "오늘 팔린 스테이크 개수"를 누적할 Counter (덧셈기) 생성
steak_counter = meter.create_counter("steaks_sold", description="오늘 판매된 스테이크 총 개수")

def serve_food():
    # 스테이크가 하나 나갈 때마다 카운터를 1씩 증가시킵니다.
    # 태그를 달아두면 나중에 "안심(Tenderloin)이 몇 개 팔렸나?" 필터링할 수 있습니다.
    steak_counter.add(1, {"steak_type": "Tenderloin"})
    print("스테이크 서빙 완료!")
```
**설명:** 여기서 `add(1)` 된 숫자들은 계속 쌓였다가 보통 1분(설정한 주기)에 한 번씩 압축된 숫자로 전송됩니다. 로그스토리지 비용을 획기적으로 절약하면서도 가장 명확한 알람 지표가 됩니다.

---

## 3. Log (로그) - 구체적인 사건 일지 ✍️
**목적:** 에러 원인을 파악하기 위한 텍스트를 남깁니다. 

🚀 **중요 포인트:** 일반 `print()`나 평범한 `logging` 모듈과 다르게 작동합니다. OpenTelemetry 환경에서는 **아래의 로그 코드가 실행될 때 1번의 'Trace 환경' 안에 있다면, 해당 로그에 자동으로 Trace ID가 도장처럼 찍힙니다.**

```python
import logging

logger = logging.getLogger("my-python-app")
logger.setLevel(logging.INFO)

def process_payment(amount: int):
    # 아래 코드가 아까 선언한 "Process_Order_Request" Trace 구간(Span) 안에서 실행된다면?
    logger.info(f"결제를 시도합니다. 금액: {amount}원")
    
    try:
        # 결제 로직 시뮬레이션
        if amount > 100000:
            raise Exception("카드 단말기 통신 에러: 잔액 부족")
    except Exception as e:
        # 이 에러 로그 역시 "어떤 주문(Trace ID)"에서 발생한 에러인지 
        # Application Insights가 자동으로 하나로 합쳐서(Correlation) 보여줍니다!
        logger.error(f"결제 실패! 사유: {e}")
```

---

## 💡 요약: 이 세 가지가 하나로 합쳐진 파이썬 코드
위의 모든 개념이 모여 실제 FastAPI 라우터에서 동작하는 모습입니다.

```python
@app.post("/order")
async def create_order(request: Request):
    # 1. 자동/수동 트레이스 시작
    with tracer.start_as_current_span("Checkout_Flow") as span:
        span.set_attribute("Client_IP", request.client.host)  # [Trace] 속성(5W1H) 첨부
        
        # 2. 메트릭 증가
        steak_counter.add(1)  # [Metric] 결제 버튼 클릭수 1 증가
        
        try:
            # 3. 로그 작성 (Trace ID와 자동 결합됨!)
            logger.info("결제 절차가 시작되었습니다.")  # [Log]
            
            # DB 연결 등 실제 복잡한 작업을 함수로 수행
            process_payment(50000) 

        except Exception as e:
            # 4. 에러 로그 작성 
            logger.error("주문 처리 중 치명적인 에러가 발생했습니다.") # [Log]
            # OTel Span에 에러 상태 기록 (빨간색으로 표시됨)
            span.set_status(trace.StatusCode.ERROR, str(e))
            
            return {"status": "fail"}
            
    return {"status": "success"}
```
**이 코드가 주는 가치:** 이렇게 코딩해 두면, 나중에 에러가 터졌을 때 그 사용자의 텍스트 에러 **로그(Log) 한 줄만 찾아도, 그 사용자가 거쳐간 모든 함수 흐름 타임라인(Trace)과 당시 식당 전체의 총 판매량 현황(Metric)까지 한 화면에서 클릭 몇 번으로 전부 추적**할 수 있게 됩니다.
