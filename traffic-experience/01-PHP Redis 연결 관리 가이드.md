---
title: "PHP Redis 연결 관리 가이드"
date: 2025-11-27
tags: ["Redis", "PHP"]
source: https://app.notion.com/p/2b8b71c012578077aee8e5c162c49160
---

# PHP Redis 연결 관리 가이드

## 💡 PHP Redis 연결 관리 가이드

---

## 1. 개요 - Redis 연결 관리

### 1.1 <code>connect()</code> vs <code>pconnect()</code>

| **특징** | **connect() - 일반 연결** | **pconnect() - 영속 연결 (Persistent Connection)** |
|---|---|---|
| **연결 생성** | 매번 새로운 **TCP 연결 생성** | **PHP 프로세스 레벨**에서 연결 유지 |
| **연결 종료** | 스크립트 종료 또는 <code>close()</code> 호출 시 종료 | PHP-FPM 워커 프로세스가 살아있는 동안 유지 (<code>close()</code> 호출해도 **닫히지 않음**) |
| **재사용** | ❌ 재사용 불가 | ✅ 여러 요청 간 연결 재사용 |
| **오버헤드** | 요청마다 연결 생성/종료 **오버헤드 발생** | 오버헤드 최소화 |

### 1.2 <code>persistent_id</code>의 중요성 ⭐

<code>pconnect()</code> 사용 시 **<code>persistent_id</code>****를 반드시 명시**해야만 연결이 재사용됩니다.

- **❌ 잘못된 사용 (persistent\_id 없음)**PHP
  ```txt
  for ($i = 0; $i < 5; $i++) {
      $redis = new Redis();
      $redis->pconnect('127.0.0.1', 6379, 2.0, null); // null
  }
  // 결과: 5개의 연결 생성 (재사용 안됨)
  
  ```
- **✅ 올바른 사용 (persistent\_id 명시)**PHP
  ```txt
  for ($i = 0; $i < 5; $i++) {
      $redis = new Redis();
      $redis->pconnect('127.0.0.1', 6379, 2.0, 'app_redis_main');
  }
  // 결과: 1개의 연결만 생성 후 재사용
  
  ```

> 핵심: persistent\_id를 명시하지 않으면 매번 새로운 persistent ID가 자동 생성되어 연결 재사용 효과가 없습니다.

### 1.3 Redis 연결 개수 계산

### a. 환경별 연결 개수 계산 공식

| **환경** | **계산 공식** | **예시 (PHP-FPM 50, 웹 서버 3대)** | **최대 연결 수** |
|---|---|---|---|
| **Standalone/Sentinel** | PHP-FPM 워커 수 X 웹 서버 대수 | 50 x 3 | **150개** |
| **Redis Cluster** | PHP-FPM 워커 수 X 웹 서버 대수 X 클러스터 노드 수 | 50 x 3 x 6 (노드 6개 가정) | **900개** |

---

### b. 계산 원리 설명

### b.1 Standalone/Sentinel 환경 🌐

이 환경에서는 PHP-FPM 워커 프로세스당 **하나의 영속 연결**이 Redis 서버로 유지됩니다.

- **원리**: <code>pconnect</code>와 <code>persistent_id</code>를 사용하면, **같은 PHP-FPM 워커 프로세스**는 모든 요청에서 Redis 서버의 **단일 연결**을 재사용합니다.
- **결과**: Redis 서버로의 **총 연결 개수**는 단순히 Redis에 접속하는 **전체 PHP-FPM 워커 프로세스의 수**와 같습니다.

> PHP-FPM 워커 수 X 웹 서버 대수

### b.2 Redis Cluster 환경 🧱

Redis Cluster는 데이터를 여러 개의 노드(Shard)에 분산 저장합니다. 클라이언트(PHP-FPM 워커)는 데이터를 읽거나 쓰기 위해 해당 데이터를 가진 노드와 직접 연결해야 합니다.

- **원리**: <code>phpredis</code> 라이브러리는 클러스터 내의 **모든 마스터 및 슬레이브 노드**와 연결을 유지하려고 시도합니다. 각 PHP-FPM 워커는 클러스터 내의 **모든 노드**에 대해 **영속 연결**을 생성할 수 있습니다.
- **결과**: Redis 서버로의 총 연결 개수는 워커 수에 **모든 클러스터 노드의 수**를 곱한 값이 됩니다. 이는 Redis 서버가 감당해야 하는 **최대 연결 수**를 의미합니다.

> PHP-FPM 워커 수 X 웹 서버 대수 X 클러스터 노드 수

**⚠️ 참고:** 클러스터 환경의 **실제 사용 연결**은 900개보다 적을 수 있으나, Redis 서버의 **<code>maxclients</code>** 설정은 이 \*\*최대치 (900개)\*\*를 수용할 수 있도록 충분히 높게 설정해야 합니다.

### 1.4 <code>pconnect()</code> 권장 파라미터

PHP

```txt
$redis->pconnect(
    string $host,              // Redis 호스트
    int $port = 6379,          // Redis 포트
    float $timeout = 0.0,      // 연결 타임아웃 (초)
    string $persistent_id = null, // 영속 연결 식별자 (중요!)
    int $retry_interval = 0,   // 재시도 간격 (밀리초)
    float $read_timeout = 0.0, // 읽기 타임아웃 (초)
    array $context = null      // 스트림 컨텍스트 (TLS 등)
);

```

**권장 설정:**

PHP

```txt
$redis->pconnect(
    $config['host'],
    $config['port'],
    2.0,                      // 연결 타임아웃: 2초
    'app_redis_main',         // persistent_id 반드시 지정!
    0,                        // 재시도 안함
    0                         // 기본 읽기 타임아웃 사용
);

```

---

## 2. Singleton 패턴 적용 이유

<code>pconnect</code>는 **PHP 프로세스 레벨**에서 연결을 관리하고, **Singleton** 패턴은 **PHP 객체 레벨**에서 인스턴스를 관리하여 이중으로 연결을 보호합니다.

### 2.1 이중 보호 메커니즘

| **보호 단계** | **메커니즘** | **관리 레벨** | **효과** |
|---|---|---|---|
| **1차 보호** | **Singleton 패턴** | PHP **객체** 레벨 | <code>getInstance()</code>로 동일 객체 보장 |
| **2차 보호** | **<code>pconnect</code>** **+** **<code>persistent_id</code>** | PHP **프로세스** 레벨 | <code>getInstance()</code> 누락시에도 연결 재사용 보호 |

### 2.2 Standalone/Sentinel 환경 (다중 DB 사용)

Standalone/Sentinel 환경에서는 \*\*DB 번호\*\*를 사용하여 데이터를 분리합니다.

- **Singleton 없이 사용 시 문제점:**
  - <code>pconnect</code>가 있어도 여러 컴포넌트에서 서로 다른 DB 번호(<code>DB 0</code>, <code>DB 1</code> 등)를 선택하여 **같은 연결을 공유할 경우** DB 번호가 충돌하여 **서로의 데이터에 영향을 줄 수 있습니다**.
- **Singleton 적용 시 해결:**
  - Redis 객체를 하나만 생성하고 공유하여 **DB 선택 상태를 유지**할 수 있습니다.
  - 각 서비스는 <code>select(DB_NUM)</code>을 초기화 시 한 번만 호출하면 됩니다.

PHP

```txt
// ✅ 올바른 패턴 (Singleton 사용)
class CacheService {
    private $redis;

    public function __construct() {
        $this->redis = \App\Libraries\Redis::getInstance();
        $this->redis->redis->select(1); // 💡 초기화 시 한번만 DB 1 선택
    }
    // ...
}

```

### 2.3 Redis Cluster 환경

Cluster 환경에서는 **오직 DB 0만 사용**하며 <code>SELECT</code> 명령어가 작동하지 않습니다.

- **Singleton의 의미:** DB 충돌 걱정은 없지만, Singleton은 **객체의 재사용**을 보장하여 **메모리 낭비**와 불필요한 객체 생성을 막아줍니다.

| **환경** | **DB 번호 사용** | **Singleton 필요성** | **주된 이유** |
|---|---|---|---|
| **Standalone** | 0-15 | ⭐⭐⭐ **필수** | DB 충돌 방지 + 연결/객체 재사용 |
| **Sentinel** | 0-15 | ⭐⭐⭐ **필수** | DB 충돌 방지 + 연결/객체 재사용 |
| **Cluster** | 0만 | ⭐⭐ **권장** | 객체 재사용 + 메모리 절약 |

### 2.4 권장 구현 패턴

PHP

```txt
// app/Libraries/Redis.php
class Redis
{
    private $redis;
    private static $instance;

    private function __construct()
    {
        $config = config('RedisConf')->config;
        $this->redis = new \Redis();

        // pconnect + persistent_id (필수)
        $this->redis->pconnect(
            $config['host'],
            $config['port'],
            $config['timeout'],
            'app_redis_main' // persistent_id 명시
        );

        if (!empty($config['password'])) {
            $this->redis->auth($config['password']);
        }
    }

    // Singleton
    public static function getInstance()
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    // Clone, Unserialize 방지
    private function __clone() {}
    private function __wakeup() {}
}

```

---

## 3. <code>reset()</code> 함수 사용처

<code>$redis->reset()</code>은 영속 연결(<code>pconnect</code>)을 닫지 않고, 해당 연결의 **Redis 서버 측 상태를 초기화**합니다.

### 3.1 <code>reset()</code>이 하는 일

- **초기화되는 것:**
  - ✅ 선택된 **DB 번호** (→ 0으로 복귀)
  - ✅ **MULTI** 트랜잭션 상태
  - ✅ **WATCH**된 키들
  - ✅ PubSub 구독, 파이프라인 모드
- **유지되는 것:**
  - ❌ TCP 연결 (유지됨)
  - ❌ 인증(<code>auth</code>) 상태

### 3.2 Standalone/Sentinel 환경에서의 사용

다중 DB를 사용하는 환경에서 <code>reset()</code>은 연결을 다음 사용자에게 반환하기 전에 상태를 정리하는 유용한 도구입니다.

- **사용 예시 1: DB 번호 초기화**PHP
  ```txt
  $redis->select(5);
  echo $redis->getDbNum(); // 5
  $redis->reset();
  echo $redis->getDbNum(); // 0
  
  ```
- **사용 예시 2: 연결 풀 반환 전 초기화**
  > 다음 요청이 이전 요청의 DB 선택, 트랜잭션 상태 등의 영향을 받지 않도록 합니다.

### 3.3 Redis Cluster 환경에서의 의미

| **환경** | **reset() 필요성** | **주 용도** |
|---|---|---|
| **Standalone** | ⭐⭐⭐ **유용** | DB 초기화, 트랜잭션 정리 |
| **Sentinel** | ⭐⭐⭐ **유용** | DB 초기화, 트랜잭션 정리 |
| **Cluster** | ⭐ **거의 불필요** | DB가 항상 0이므로, 주로 트랜잭션 취소는 <code>discard()</code> 사용 권장 |

---

## 4. Predixy 프록시 이해하기

**Predixy**는 Redis Cluster나 Sentinel 환경에서 클라이언트와 Redis 서버 사이에 위치하여 **연결 관리**, **자동 라우팅**, **고가용성** 등을 제공하는 전용 프록시 서버입니다.

### 4.1 주요 기능

- **연결 관리**: 클라이언트와 서버 연결을 분리하고 연결 풀링으로 Redis 서버의 부하를 줄입니다.
- **자동 라우팅**: Cluster 환경에서 키의 해시 슬롯에 따라 노드로 자동 라우팅합니다.
- **고가용성**: Master/Slave Failover를 자동으로 감지합니다.
- **읽기 분산**: Slave 노드를 활용하여 읽기 부하를 분산합니다.

### 4.2 Predixy 확인 방법

Predixy에 연결 후 <code>INFO server</code> 명령을 실행하여 확인합니다.

Bash

```txt
redis-cli -h 127.0.0.1 -p 6379
127.0.0.1:6379> INFO server
# Proxy
...
RedisMode:proxy # ← Predixy임을 나타냄

```

### 4.3 Predixy 환경에서의 제한사항

- **CONFIG 명령어 제한**: <code>CONFIG GET databases</code>와 같은 서버 설정 관련 명령어는 Predixy를 통하면 작동하지 않거나 제한적일 수 있습니다.
- **해결**: 백엔드 Redis 서버에 **직접 접속**하여 해당 명령어를 실행해야 합니다.

### 4.4 Predixy vs 직접 연결 비교

| **특징** | **직접 연결** | **Predixy 사용** |
|---|---|---|
| **연결 관리** | 애플리케이션이 직접 (pconnect) | **Predixy가 관리** (연결 풀링) |
| **Failover** | 수동 처리/센티넬 클라이언트 | **자동 처리** |
| **읽기 분산** | 직접 구현 필요 | **자동 처리** |
| **지연시간** | 낮음 | 약간 높음 (프록시 홉) |
| **CONFIG 명령어** | ✅ 가능 | ⚠️ 제한적 |

---

## 5. PHP Redis 사용 시 유의사항

### 5.1 TCP <code>TIME_WAIT</code> 문제

<code>connect()</code>를 반복적으로 사용하여 짧은 시간 내에 많은 연결을 생성하고 종료하면, 해당 포트가 <code>TIME_WAIT</code> 상태로 약 60초간 유지되어 **포트가 고갈**되고 *“Cannot assign requested address”* 에러가 발생할 수 있습니다.

- **해결책 1 (권장)**: \*\*<code>pconnect()</code>\*와 **Singleton 패턴**을 사용하여 연결을 재사용합니다.
  - 영속 연결은 연결을 닫지 않으므로 <code>TIME_WAIT</code> 상태가 발생하지 않습니다.
- **시스템 레벨 설정 (선택 사항)**: <code>/etc/sysctl.conf</code>에 <code>net.ipv4.tcp_tw_reuse = 1</code>을 설정하여 <code>TIME_WAIT</code> 상태의 소켓 재사용을 허용할 수 있으나, **보안 및 트래픽 재전송 문제**를 고려해야 합니다.

### 5.2 타임아웃 및 직렬화 설정

| **설정** | **권장 값** | **설명** |
|---|---|---|
| **연결 타임아웃** | <code>2.0</code> (2초) | <code>pconnect($host, $port, 2.0, ...)</code> |
| **읽기 타임아웃** | <code>3.0</code> (3초) | <code>$redis->setOption(Redis::OPT_READ_TIMEOUT, 3.0)</code> |
| **직렬화** | <code>SERIALIZER_IGBINARY</code> | **IGBINARY**는 PHP 기본 직렬화보다 빠르고 메모리를 절약합니다. (설치 필요) |

### 5.3 대용량 데이터 처리 및 서버 부하 방지

- **<code>KEYS</code>** **명령어 사용 금지**
  - 프로덕션 환경에서 서버를 블로킹할 수 있습니다.
  - ✅ **<code>SCAN</code>** **명령어**를 사용하여 점진적으로 키를 탐색합니다.
- **파이프라인 사용**
  - 여러 명령을 한 번의 왕복(Round Trip)으로 묶어 지연 시간을 줄입니다.
  - ✅ **<code>$redis->multi(Redis::PIPELINE)</code>** → 명령 실행 → **<code>$redis->exec()</code>**

### 5.4 PHP-FPM 설정 고려

- **<code>pm.max_children</code>**: 워커 프로세스 수는 Redis 연결 개수에 직접적인 영향을 줍니다.
- **<code>pm.max_requests</code>**: 워커 프로세스가 일정 수의 요청을 처리한 후 **재시작**되도록 설정하여, <code>pconnect</code>로 인해 누적될 수 있는 **메모리나 상태 문제를 주기적으로 정리**할 수 있습니다.

### 5.5 최종 체크리스트 ✅

| **필수 적용 사항** | **권장 사항** |
|---|---|
| ✅ **<code>pconnect()</code>** **+** **<code>persistent_id</code>** 사용 | ⭐ 파이프라인 활용 |
| ✅ **Singleton 패턴** 적용 | ⭐ 직렬화 최적화 (<code>igbinary</code>) |
| ✅ **타임아웃** 설정 (연결, 읽기) | ⭐ 대용량 데이터 **압축/분할** |
| ✅ **<code>try-catch</code>** 에러 처리 | ⭐ PHP-FPM <code>pm.max_requests</code> 설정 |
| ✅ **<code>KEYS</code>** **대신** **<code>SCAN</code>** 사용 | ⭐ Redis <code>maxclients</code> 충분히 설정 |
| ✅ **TTL** 설정으로 메모리 관리 | ⭐ 모니터링 구현 |

---

## 📚 참고 자료

- phpredis: [https://github.com/phpredis/phpredis](https://github.com/phpredis/phpredis)
- Redis 공식 문서: [https://redis.io/docs/](https://redis.io/docs/)
- Predixy: [https://github.com/joyieldInc/predixy](https://github.com/joyieldInc/predixy)
