## VM에서 서버 올리기
```bash
nohup python3 dummy_app.py &
```

## 제대로 떳는지 확인 (프로세스 확인)
```bash
ps -ef | grep dummy_app.py
```

## 제대로 떳는지 확인 (프로세스 확인)
```bash
kill -9 <PID>
```

## 실시간으로 쌓이는 로그를 계속 지켜보고 싶다면 
```bash
tail -f nohup.out

# Ctrl + C 로 tail모드 종료
```