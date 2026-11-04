---
title: "Connection TIME_WAIT 측정"
date: 2025-12-04
tags: ["Redis", "MariaDB", "네트워크"]
source: https://app.notion.com/p/2bfb71c01257806997bfcda1a89aab89
---

# Connection TIME_WAIT 측정

## 개요

Redis 캐시 서버 연결 방식을 개선하여 시스템 리소스 낭비를 제거하고 성능을 향상시켰습니다.

---

## TIME\_WAIT이란?

**TIME\_WAIT**은 네트워크 연결이 종료될 때 발생하는 대기 상태입니다.

### 발생 시점

```txt
사용자 요청 → Redis 연결 → 작업 수행 → 연결 종료 → TIME_WAIT 발생 (60~120초 대기)

```

### 왜 문제가 되나?

- **리소스 낭비**: 각 TIME\_WAIT마다 시스템 메모리와 포트 사용
- **포트 고갈**: 동시에 사용 가능한 포트가 제한적 (보통 28,000\~60,000개)
- **성능 저하**: 매번 새로운 연결을 생성하는 오버헤드

**예시:**

- 초당 100개 요청 × 60초 대기 = 6,000개 TIME\_WAIT 누적
- 장시간 운영 시 수만 개의 불필요한 대기 상태 발생

---

## 개선 방안

### 1. 싱글턴 패턴 (Singleton Pattern)

**의미:** 프로그램 전체에서 Redis 연결 객체를 딱 한 번만 생성하고 재사용

**효과:**

- 연결을 닫지 않고 계속 재사용
- TIME\_WAIT 발생 방지

---

### 2. pconnect (영구 연결)

**의미:** 일반 연결(connect) 대신 영구적으로 유지되는 연결(pconnect) 사용

**효과:**

- 요청이 끝나도 연결을 유지
- TIME\_WAIT 발생 방지
- 다음 요청에서 기존 연결 즉시 재사용

---

## 테스트 결과

### 테스트 조건

- ENDPOINT 요청 횟수: 100회
- 1개의 요청 내에 REDIS 연결 요청 횟수 : 10회
- php child 갯수 : 30개
- 측정 항목: TIME\_WAIT 소켓 개수

### 측정 결과

| 연결 방식 | 설명 | TIME\_WAIT 증가량 | 평가 |
| --- | --- | --- | --- |
| 싱글턴 O + pconnect | 현재 배포 방식 | php child 갯수 (30) = 30 | 최우수 |
| 싱글턴 O + connect | 싱글턴 + 일반 연결 | 요청 횟수(100)  = 100 | 불량 |
| 싱글턴 X + pconnect | 영구 연결만 사용 | php child 갯수(30) \* 2 = 60 | 우수 |
| 싱글턴 X + connect | 배포 전 방식 | 요청 횟수(100) \* 요청 내부 연결 횟수(10)  = 1000 | 불량 |

---

## 배포 전후 비교

### 배포 전 (문제 상황)

**동작 방식:**

1. 사용자 요청마다 새로운 Redis 연결 생성
2. 작업 완료 후 연결 종료
3. TIME\_WAIT 발생 (60\~120초 대기)

**문제점:**

- 100개 요청 → 100개 \* connection 수 만큼의 TIME\_WAIT 발생
- 시스템 리소스 지속적 낭비
- 포트 고갈 위험

---

### 배포 후 (개선)

**동작 방식:**

1. 요청당 1회만 Redis 연결 생성
2. 기존 연결 재사용

**개선 효과:**

- TIME\_WAIT 30개
- 연결 생성 오버헤드 제거
- 시스템 리소스 효율적 사용

---

## 검증 방법

실시간으로 TIME\_WAIT 상태를 모니터링하여 개선 효과를 확인할 수 있습니다:

```bash
# 1초마다 TIME_WAIT 개수 확인
watch -n 1 "netstat -an | grep :6379 | grep TIME_WAIT | wc -l"

```

## AB 테스트 방법

```javascript
// AB 테스트 설치
sudo apt-get install apache2-utils

// n : 총 몇번을 보낼지, -c : 병렬 요청 (한번에 몇개 보낼지), -p : body 데이터 파일, -T : Content-Type
ab -n 1000 -c 50 -p data.json -T application/json http://localhost/
```
