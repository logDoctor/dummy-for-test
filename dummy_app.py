import time
import random
import json
import string
from datetime import datetime, timezone

LOG_FILE_PATH = "diet_web_app.log"

# 📉 다이어트 1: 가짜 스택 트레이스 용량을 5KB에서 1KB로 대폭 축소
def generate_garbage_payload(size_kb=1):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=int(size_kb * 1024)))

endpoints = [
    # 비율은 기존의 악랄함을 유지합니다 (KQL 필터링 효과를 극적으로 보여주기 위함)
    {"method": "POST", "path": "/api/v1/payment/checkout", "status": 200, "level": "INFO", "weight": 1},
    {"method": "GET",  "path": "/health", "status": 200, "level": "INFO", "weight": 50},
    {"method": "GET",  "path": "/assets/main.chunk.js.map", "status": 200, "level": "INFO", "weight": 20},
    {"method": "TRACE", "path": "/internal/db/sync", "status": 200, "level": "DEBUG", "weight": 25},
    {"method": "POST", "path": "/api/v1/auth/login", "status": 503, "level": "ERROR", "weight": 4}
]

def generate_log(endpoint):
    log_entry = {
        "TimeGenerated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "LogLevel": endpoint["level"],
        "HttpMethod": endpoint["method"],
        "RequestUri": endpoint["path"],
        "StatusCode": endpoint["status"],
        "ResponseTimeMs": random.randint(10, 500)
    }
    
    if endpoint["level"] == "DEBUG":
        log_entry["Message"] = f"Executing trace: DB connection pool full. DUMP: {generate_garbage_payload(1)}"
    else:
        log_entry["Message"] = f"Processed request for {endpoint['path']}"
        
    return log_entry

if __name__ == "__main__":
    print(f"🥗 [다이어트 모드] 안전한 더미 앱을 시작합니다.")
    print(f"📁 로그 기록 위치: {LOG_FILE_PATH}")
    print("종료하려면 Ctrl+C를 누르세요.\n")
    
    weights = [ep["weight"] for ep in endpoints]
    
    try:
        with open(LOG_FILE_PATH, "a") as f:
            while True:
                endpoint = random.choices(endpoints, weights=weights, k=1)[0]
                
                # 📉 다이어트 2: 에러 발생 시 폭주량을 50개에서 10개로 축소
                burst_count = 10 if endpoint["level"] == "ERROR" else 1
                
                for _ in range(burst_count):
                    log_data = generate_log(endpoint)
                    f.write(json.dumps(log_data) + "\n")
                    f.flush()
                    
                    if burst_count == 1:
                        print(f"[{log_data['TimeGenerated']}] [{log_data['LogLevel']}] {log_data['RequestUri']} (Size: {len(str(log_data))} bytes)")
                    
                if burst_count > 1:
                    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    print(f"[{current_time}] 🔥 [RETRY STORM] {endpoint['path']} 장애로 {burst_count}개의 로그가 발생했습니다!")
                
                # 📉 다이어트 3: 로그 생성 주기를 평균 1초(0.5초 ~ 1.5초)로 확 늦춤
                time.sleep(random.uniform(0.5, 1.5))
                
    except KeyboardInterrupt:
        print("\n🛑 더미 앱을 종료합니다.")