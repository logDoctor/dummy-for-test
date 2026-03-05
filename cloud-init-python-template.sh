#!/bin/bash
# =================================================================
# cloud-init-python-template.sh
# 플레이스홀더: __CONN_STR__ __VM_USER__ __REPO_URL__
# PowerShell에서 실제값으로 치환 후 VM custom-data로 사용
# =================================================================
set -e
exec > /var/log/cloud-init-app.log 2>&1

echo "=== [1/5] cloud-init 시작 ==="

apt-get update -y
apt-get install -y python3-pip python3-venv git curl

echo "=== [2/5] 레포 클론 ==="
cd /home/__VM_USER__
git clone __REPO_URL__ dummy-for-test
chown -R __VM_USER__:__VM_USER__ dummy-for-test

echo "=== [3/5] Python 의존성 설치 ==="
cd /home/__VM_USER__/dummy-for-test/samples/python
python3 -m venv .venv
.venv/bin/pip install --quiet -r requirements.txt

echo "=== [4/5] 앱 실행 ==="
# 환경변수 영구 등록
echo "APPLICATIONINSIGHTS_CONNECTION_STRING=__CONN_STR__" >> /etc/environment

# 앱 백그라운드 실행
sudo -u __VM_USER__ bash -c "
  export APPLICATIONINSIGHTS_CONNECTION_STRING='__CONN_STR__'
  cd /home/__VM_USER__/dummy-for-test/samples/python
  nohup .venv/bin/uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 \
    > /home/__VM_USER__/app.log 2>&1 &
  echo \$! > /home/__VM_USER__/app.pid
  echo 'FastAPI PID: '\$!
"

echo "=== [5/5] 트래픽 자동 생성 (앱 기동 대기 25초) ==="
sleep 25

for i in {1..5}; do
  echo "--- 트래픽 라운드 $i / 5 ---"
  curl -sf http://localhost:8000/api/                              > /dev/null || true
  curl -sf http://localhost:8000/api/health                        > /dev/null || true
  curl -sf http://localhost:8000/api/logs                          > /dev/null || true
  curl -sf http://localhost:8000/api/custom-event                  > /dev/null || true
  curl -sf http://localhost:8000/api/dependency                    > /dev/null || true
  curl -sf http://localhost:8000/api/secret-data                   > /dev/null || true
  curl -sf http://localhost:8000/api/error                         > /dev/null || true
  curl -sf 'http://localhost:8000/api/normalized-log?scenario=good' > /dev/null || true
  curl -sf 'http://localhost:8000/api/normalized-log?scenario=bad'  > /dev/null || true
  sleep 5
done

echo "=== 완료! Azure Portal -> ai-logdoctor-test -> Transaction search 에서 확인하세요 ==="
