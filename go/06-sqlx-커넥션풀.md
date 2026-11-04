---
title: "06. PHP는 요청마다 DB에 붙는데, Go는 커넥션을 어떻게 관리할까? (sqlx와 커넥션 풀)"
date: 2026-11-04
tags: ["Go"]
---

# 06. PHP는 요청마다 DB에 붙는데, Go는 커넥션을 어떻게 관리할까? (sqlx와 커넥션 풀)

**Go 학습 · 06**

PHP-FPM에서는 요청이 끝나면 DB 커넥션도 같이 끊겨서 커넥션 관리를 따로 고민할 일이 별로 없었어요. Go 서버는 프로세스 하나가 계속 떠 있어서 이야기가 달라져요. `database/sql` 이 품고 있는 커넥션 풀이 어떻게 도는지, 설정 네 개를 어떻게 고르는지, sqlx가 뭘 편하게 해 주는지 정리해요. 예제는 Go 1.26, sqlx v1.4.0, go-sql-driver/mysql v1.10.1, 로컬 MySQL 9.2, PHP 7.4.33 에서 직접 돌려 본 결과예요.

| 항목 | 내용 |
|---|---|
| 궁금했던 것 | PHP는 요청마다 DB에 붙었다 끊는데, Go는 커넥션을 어떻게 관리해? |
| 한 줄 답 | Go는 프로세스에 `*sql.DB` 하나를 만들어 두고, 그 안의 커넥션 풀에서 커넥션을 빌렸다 돌려줘요. 요청마다 새로 붙지 않으니 빠르지만, 풀 크기와 수명은 우리가 직접 정해 줘야 해요. |
| 정리한 날 | 2026-11-04 |
| 같이 볼 글 | Go 학습 내용 · [01. Go 서버는 데몬을 띄워야 돌아갈까?](01-실행방식.md) · [02. 고루틴과 스프링 스레드](02-goroutine-spring.md) · [03. PHP 7.4와 문법 차이](03-php-문법차이.md) · [05. gin으로 API 만들기](05-gin-api.md) |

## 01. 한 줄 답: 붙었다 끊지 않고, 빌렸다 돌려줘요

PHP-FPM은 요청이 들어오면 워커가 DB에 붙고, 요청이 끝나면 끊어요. Go는 서버가 뜰 때 `sql.Open` 을 한 번 부르고, 이후에는 쿼리할 때마다 풀에서 커넥션을 하나 빌렸다가 끝나면 돌려줘요. 커넥션은 끊기지 않고 다음 고루틴이 다시 써요.

> 💡 `*sql.DB` 는 "커넥션 하나"가 아니라 "커넥션 풀"이에요. 프로세스에 하나만 만들어서 모든 고루틴이 같이 써요.

> 📌 PHP-FPM\
> **요청 하나 = 연결 한 번**\
> 요청이 끝나면 끊겨요. 커넥션 수는 대략 FPM 워커 수만큼 생겨요.

> 📌 Go database/sql\
> **프로세스 하나 = 풀 하나**\
> 커넥션을 재사용해요. 최대 개수, 놀고 있는 개수, 수명을 직접 정해요.

> 📌 스프링 HikariCP\
> **Go랑 거의 같은 방식**\
> 앱이 풀을 들고 있어요. 설정 이름만 다르고 고민할 거리는 똑같아요.

## 02. 공용 자전거로 비유하면

- **PHP-FPM** — 갈 때마다 자전거를 새로 사서 타고, 도착하면 버려요. 매번 사는 시간(TCP 연결, 인증)이 들고, 버린 자전거(끊긴 소켓)가 한동안 길가에 쌓여요.
- **Go** — 회사 앞에 공용 자전거 거치대가 있어요. 고루틴은 거치대에서 자전거를 빌려 타고, 다 쓰면 다시 꽂아 둬요. 거치대 크기(`SetMaxOpenConns`)보다 사람이 많으면 누가 반납할 때까지 줄 서서 기다려요.

"버린 자전거"가 바로 TIME_WAIT예요. TCP는 먼저 끊은 쪽에 소켓이 잠깐(macOS 기준 수십 초) 남아요. 요청마다 붙었다 끊으면 그만큼 쌓여요. 직접 세어 봤어요.

```
# 로컬 MySQL에 "요청 100번"을 흉내 내고 TIME_WAIT 소켓 수를 셌어요
PHP 7.4 mysqli, 요청마다 연결·종료 100번   → TIME_WAIT 119개 (시작할 때 15개)
Go, 요청마다 sql.Open·Close 100번         → TIME_WAIT 105개, 새 연결 100번
Go, *sql.DB 하나로 Ping 100번             → TIME_WAIT 2개,   새 연결 1번
```

TIME_WAIT는 연결을 먼저 끊은 클라이언트 쪽(PHP 서버)에 쌓여요. 트래픽이 많으면 로컬 포트가 모자라서 새 연결이 실패할 수도 있어요. PHP에서는 이걸 피하려고 `mysqli` 의 `p:` 접두어나 `PDO::ATTR_PERSISTENT` 로 지속 연결을 쓰기도 했죠. 그런데 지속 연결은 워커마다 하나씩 붙잡고 있는 방식이라, 워커 수 × 서버 수만큼 MariaDB 커넥션이 늘 열려 있어요. 놀고 있는 워커도 커넥션을 쥐고 있어요.

Go 풀은 둘의 중간이에요. 재사용해서 TIME_WAIT가 거의 안 생기고, 최대 개수를 정해 두니 MariaDB 커넥션 수도 예측할 수 있어요.

## 03. 풀 설정 네 개 고르기

```go
// main.go — 프로세스가 뜰 때 딱 한 번만 해요
db, err := sqlx.Open("mysql", "app:pass@tcp(db-host:3306)/app?parseTime=true&loc=UTC")
if err != nil {
    log.Fatal(err)
}
db.SetMaxOpenConns(20)                  // 동시에 열 수 있는 최대 개수
db.SetMaxIdleConns(20)                  // 놀고 있어도 남겨 둘 개수
db.SetConnMaxLifetime(5 * time.Minute)  // 만든 지 이만큼 지나면 새로 바꿔요
db.SetConnMaxIdleTime(2 * time.Minute)  // 이만큼 놀았으면 닫아요

if err := db.PingContext(ctx); err != nil {  // Open은 실제로 연결을 안 해요
    log.Fatal(err)
}
```

| 설정 | 기본값 | 어떻게 고를까 |
|---|---|---|
| `SetMaxOpenConns` | 0 (무제한) | **꼭 정해요.** 무제한이면 고루틴이 몰릴 때 커넥션도 끝없이 늘어서 MariaDB `max_connections` 에 부딪혀요. 파드 수까지 곱해서 계산해요(08장). |
| `SetMaxIdleConns` | 2 | 보통 MaxOpen이랑 같게 둬요. 기본값 2로 두면 바쁠 때 열었던 커넥션을 반납하자마자 닫아 버려서, 결국 PHP처럼 붙었다 끊기를 반복해요. |
| `SetConnMaxLifetime` | 0 (영원히) | MariaDB `wait_timeout` 이나 중간 L4, 방화벽의 유휴 타임아웃보다 **확실히 짧게** 잡아요. 드라이버 README는 5분 이하를 권해요. |
| `SetConnMaxIdleTime` | 0 (영원히) | 트래픽이 빠진 뒤 놀고 있는 커넥션을 정리해요. 새벽에 MariaDB 커넥션 수를 줄이고 싶을 때 써요. |

### MaxIdleConns를 기본값으로 두면 진짜 다시 붙을까?

`MaxOpenConns=10`, `MaxIdleConns=2` 로 두고 고루틴 10개가 쿼리하는 걸 5번 반복해 봤어요. `MaxIdleClosed=40` 이 나왔어요. 커넥션 40개를 열자마자 닫았다는 뜻이에요. 둘을 같게 두면 0이에요.

### wait_timeout보다 짧아야 하는 이유

MariaDB는 `wait_timeout` (기본 28800초, 8시간) 동안 아무 쿼리도 없는 커넥션을 서버 쪽에서 먼저 끊어요. 풀은 그걸 모르고 그 커넥션을 계속 들고 있어요. 세션 `wait_timeout` 을 2초로 낮추고 3초 쉬었다가 쿼리해 봤어요.

```
// DSN에 wait_timeout=2 를 붙이고, 3초 쉬었다가 SELECT CONNECTION_ID()
// 풀 설정 없음
[mysql] connection.go:803 closing bad idle connection: unexpected read from socket
3초 뒤: <nil> 커넥션 ID: 26     // 첫 커넥션은 25였어요

// SetConnMaxIdleTime(1 * time.Second) 추가
3초 뒤: <nil> 커넥션 ID: 28     // 로그 없이 조용히 바뀌고, MaxIdleTimeClosed=1
```

이번엔 드라이버가 끊긴 걸 알아채고 새로 붙어서 에러까지는 안 났어요. 그래도 로그가 찍히고, 커넥션을 쓰는 도중에 끊기면 `invalid connection` 에러로 올라올 수 있어요. 풀이 먼저 정리하게 수명을 짧게 두는 게 마음 편해요.

## 04. `db.Stats()` 로 풀 들여다보기

풀이 지금 어떤지는 `db.Stats()` 한 번이면 보여요. 거치대 크기를 2로 두고 1초짜리 쿼리(`SELECT SLEEP(1)`)를 고루틴 4개가 동시에 날려 봤어요.

```
db.SetMaxOpenConns(2)
// 고루틴 4개가 동시에 db.Get(&x, "SELECT SLEEP(1)")

실행 중: Open=2 InUse=2 Idle=0 WaitCount=2 WaitDuration=0s
걸린 시간: 2s
끝난 뒤: Open=2 InUse=0 Idle=2 WaitCount=2 WaitDuration=2.013s
```

- **InUse / Idle** — 빌려 간 개수랑 거치대에 꽂혀 있는 개수예요.
- **WaitCount, WaitDuration** — 커넥션이 없어서 줄 선 횟수랑 기다린 시간의 합이에요. 2개가 1초씩 기다려서 쿼리 4개가 2초 걸렸어요. 이 숫자가 계속 오르면 풀이 작거나 커넥션을 오래 붙잡는 코드가 있다는 신호예요.
- **MaxIdleClosed, MaxIdleTimeClosed, MaxLifetimeClosed** — 설정 때문에 닫힌 개수예요. MaxIdleClosed가 빠르게 오르면 MaxIdleConns가 너무 작아요.

## 05. sqlx가 더해 주는 것

sqlx는 `database/sql` 을 감싼 얇은 라이브러리예요. ORM이 아니라 SQL은 그대로 직접 쓰고, **결과를 struct에 담는 귀찮은 일**만 줄여 줘요. 커넥션 풀도 `database/sql` 것을 그대로 써요. CodeIgniter 4로 치면 Query Builder 없이 `$db->query($sql)->getResult()` 만 쓰는 느낌이에요.

```go
type User struct {
    ID        int64          `db:"id"`          // 컬럼 이름은 db 태그로 맞춰요
    Name      string         `db:"name"`
    Nickname  sql.NullString `db:"nickname"`    // NULL 가능한 컬럼
    CreatedAt time.Time      `db:"created_at"`
}

// 한 줄: Get — 없으면 sql.ErrNoRows
var u User
err := db.GetContext(ctx, &u, "SELECT * FROM users WHERE id = ?", id)

// 여러 줄: Select — 없으면 에러 없이 빈 슬라이스(nil)
var users []User
err = db.SelectContext(ctx, &users, "SELECT * FROM users ORDER BY id")

// 이름 붙은 파라미터: NamedExec — struct 필드를 :name 자리에 넣어 줘요
res, err := db.NamedExecContext(ctx,
    `INSERT INTO users (name, nickname) VALUES (:name, :nickname)`, u)

// IN 절: sqlx.In — 슬라이스를 ?, ?, ? 로 펼쳐 줘요
q, args, err := sqlx.In("SELECT * FROM posts WHERE user_id IN (?)", []int64{1, 3})
q = db.Rebind(q)                               // 드라이버에 맞는 자리표시자로
err = db.SelectContext(ctx, &posts, q, args...)
```

돌려 보면 `sqlx.In` 은 쿼리를 `... IN (?, ?)` 와 인자 `[1 3]` 으로 바꿔 줘요. **빈 슬라이스를 넘기면 `empty slice passed to 'in' query` 에러**가 나요. 목록이 비었으면 쿼리 전에 미리 빠져나와요.

`database/sql` 만 쓰면 `rows.Next()` 를 돌면서 `rows.Scan(&u.ID, &u.Name, ...)` 를 컬럼 순서대로 직접 써야 해요. sqlx는 이걸 태그로 해결해 줘요.

## 06. 트랜잭션과 타임아웃

### 트랜잭션: BeginTxx, defer Rollback, ctx 넘기기

```go
func CreateUserWithPost(ctx context.Context, db *sqlx.DB, name, title string) error {
    tx, err := db.BeginTxx(ctx, nil)
    if err != nil {
        return fmt.Errorf("트랜잭션 시작: %w", err)
    }
    defer tx.Rollback() // Commit 이 끝났으면 아무 일도 안 해요

    res, err := tx.ExecContext(ctx, "INSERT INTO users (name) VALUES (?)", name)
    if err != nil {
        return err
    }
    uid, _ := res.LastInsertId()
    if _, err := tx.ExecContext(ctx,
        "INSERT INTO posts (user_id, title) VALUES (?, ?)", uid, title); err != nil {
        return err
    }
    return tx.Commit()
}
```

- **트랜잭션은 커넥션 하나를 통째로 빌려 가요.** `Commit` 이나 `Rollback` 을 할 때까지 그 커넥션은 풀로 안 돌아와요.
- **`defer tx.Rollback()` 을 바로 붙여요.** 중간에 `return err` 로 빠져나가도 롤백되고 커넥션이 돌아와요. 두 번째 INSERT 전에 에러를 내 봤더니 첫 INSERT도 남지 않았어요.
- **안에서는 꼭 `tx.` 로 쿼리해요.** 실수로 `db.ExecContext` 를 부르면 풀에서 다른 커넥션을 빌려서 트랜잭션 밖에서 실행돼요.
- **ctx를 넘겨요.** 요청이 취소되거나 타임아웃이 나면 `database/sql` 이 트랜잭션을 알아서 롤백해요.

### QueryContext에 타임아웃 걸기

```go
ctx, cancel := context.WithTimeout(ctx, 1*time.Second)
defer cancel()
err := db.GetContext(ctx, &x, "SELECT SLEEP(3)")

결과: context deadline exceeded 걸린 시간: 1s
타임아웃 뒤: Open=0 InUse=0 Idle=0
```

1초 만에 에러로 돌아왔어요. 눈여겨볼 건 `Open=0` 이에요. 드라이버는 쿼리 중간에 끊긴 커넥션을 재사용하지 않고 버려요. 타임아웃이 자주 나면 풀이 커넥션을 계속 새로 만들게 돼요. ctx 타임아웃을 안 걸면 느린 쿼리가 커넥션을 끝까지 붙잡아요.

## 07. PHP, 스프링과 비교

| 궁금한 것 | PHP-FPM (CI4) | Go (sqlx) | 스프링 (HikariCP) |
|---|---|---|---|
| 커넥션은 언제 생겨? | 요청마다 연결, 끝나면 종료 | 필요할 때 풀이 만들고 재사용 | 뜰 때 minimumIdle만큼 미리 만들어요 |
| 최대 개수 | `pm.max_children` 가 사실상 상한 | `SetMaxOpenConns` (기본 무제한) | `maximumPoolSize` (기본 10) |
| 커넥션 수명 | 요청 하나 | `SetConnMaxLifetime` (기본 무한) | `maxLifetime` (기본 30분) |
| 풀이 다 찼을 때 | 해당 없음 | ctx가 끝날 때까지 기다려요 | `connectionTimeout` (기본 30초) 뒤 예외 |
| 트랜잭션 전달 | `$db->transStart()` | `tx` 를 인자로 직접 넘겨요 | `@Transactional` + ThreadLocal |
| 결과 매핑 | `getResultArray()` | `db` 태그 + Get/Select | JPA, MyBatis |

HikariCP를 써 봤다면 설정 고민은 그대로 가져오면 돼요. `maxLifetime` 을 DB 타임아웃보다 몇 초 짧게 두라는 HikariCP 권고는 Go의 `SetConnMaxLifetime` 에도 똑같이 적용돼요. 다른 점은 Go에는 "풀 대기 타임아웃" 설정이 따로 없다는 거예요. 기다리는 시간은 ctx의 타임아웃이 대신 정해요. ctx 없이 `db.Query` 를 부르면 커넥션이 날 때까지 무한정 기다려요.

## 08. 조심할 것

| 조심할 것 | 왜 문제가 되는데? | 어떻게 해? |
|---|---|---|
| **`rows.Close()` 를 빼먹어요** | `db.Query` 의 rows를 닫지 않으면 커넥션이 풀로 안 돌아와요. MaxOpen=2에서 두 번 빼먹었더니 `InUse=2` 로 고정되고, 세 번째 쿼리는 2초 기다리다 `context deadline exceeded` 가 났어요. | 에러 확인 바로 다음 줄에 `defer rows.Close()`. 같은 조건에서 100번 돌려도 `InUse=0` 이었어요. sqlx Get/Select는 알아서 닫아 줘요. |
| **`sql.ErrNoRows`** | Get은 결과가 없으면 에러를 돌려줘요. Select는 에러 없이 빈 슬라이스(`nil`)예요. 둘이 달라요. | `errors.Is(err, sql.ErrNoRows)` 로 골라서 404 같은 걸로 바꿔요. `nil` 슬라이스는 JSON에서 `null` 이 되니 03편도 같이 봐요. |
| **NULL 컬럼** | NULL을 `string` 에 담으면 `converting NULL to string is unsupported` 에러가 나요. PHP는 그냥 `null` 을 줬죠. | `sql.NullString` (Valid로 확인) 이나 `*string` (nil로 확인)을 써요. 응답 JSON까지 생각하면 포인터가 편해요. |
| **`parseTime=true` 가 없어요** | DATETIME이 `[]byte` 로 와서 `time.Time` 에 못 담아요(`unsupported Scan, storing driver.Value type []uint8`). | DSN에 `parseTime=true` 를 붙여요. DATETIME에는 시간대가 없으니 `loc` 도 명시해요. |
| **요청마다 `sql.Open`** | 풀을 매번 새로 만들고 버리는 거라 PHP보다 나쁠 수도 있어요. 100번 해 보니 새 연결 100번, TIME_WAIT 105개였어요. | main에서 한 번 만들고 의존성으로 넘겨요. 테스트 코드도 마찬가지예요. |
| **트랜잭션 안에서 외부 API 호출** | API가 느리면 그동안 커넥션을 쥐고 있어요. MaxOpen=2에서 트랜잭션 2개가 2초짜리 호출을 하는 동안, 상관없는 `SELECT 1` 이 0.5초 기다리다 실패했어요. | 외부 호출은 트랜잭션 밖으로 빼요. 먼저 호출하고 결과를 들고 짧게 커밋해요. |
| **MaxOpenConns × 파드 수** | MaxOpen 20, 파드 10개면 최대 200개예요. MariaDB 기본 `max_connections` 는 151이에요. 롤링 배포 중엔 파드가 잠깐 더 늘어요. | (파드 최대 수 × MaxOpen) + 배치, 관리 도구 몫이 `max_connections` 안에 들어오게 잡아요. |

## 09. 스스로 확인해 보기

#### 1. 게시글 목록 API가 평소엔 빠른데, 하루에 몇 번 모든 API가 같이 느려져요. `db.Stats()` 를 보니 `InUse` 가 MaxOpen에 붙어 있고 `WaitCount` 가 계속 올라요. 뭘 먼저 의심할까?

<details>
<summary>답 보기</summary>

커넥션을 오래 쥐고 있는 코드를 먼저 찾아요. 1순위는 `rows.Close()` 를 빼먹은 곳, 2순위는 트랜잭션 안에서 외부 API나 파일 처리를 하는 곳, 3순위는 타임아웃 없는 느린 쿼리예요. 풀 크기를 키우는 건 원인을 없앤 다음에 해요. 먼저 키우면 MariaDB `max_connections` 에 대신 부딪혀요.

</details>

#### 2. 서버를 띄우고 밤새 트래픽이 없다가, 아침 첫 요청에서 `invalid connection` 이 한 번 났어요. MariaDB `wait_timeout` 은 600초고 풀 설정은 MaxOpen만 했어요. 왜일까?

<details>
<summary>답 보기</summary>

`SetConnMaxLifetime`, `SetConnMaxIdleTime` 이 기본값(무한)이라 풀이 밤새 커넥션을 들고 있었어요. 그사이 MariaDB가 600초 지난 커넥션을 먼저 끊었어요. 수명을 `wait_timeout` 보다 짧게(예: 5분 미만) 두면 풀이 먼저 정리해요.

</details>

이 글의 예제는 로컬 MySQL 9.2로 돌렸어요. MariaDB에서 직접 돌려 보지는 않았어요. 같은 드라이버와 같은 프로토콜이라 결과는 같을 거라고 보지만, 03장의 DSN 예시(계정, 호스트, 풀 숫자)와 08장의 파드 계산은 실행한 게 아니라 예시예요.

## 10. 참고한 글

- [\[Go\] MySQL 연결해보기](https://velog.io/@flfns333/Go-MySQL-%EC%97%B0%EA%B2%B0%ED%95%B4%EB%B3%B4%EA%B8%B0) — velog. MaxIdleConns를 MaxOpenConns와 같게, ConnMaxLifetime 5분 미만, parseTime
- [PHP Connection Pool](https://velog.io/@woooooooong/PHP-Connection-Pool) — velog. PHP에는 커넥션 풀이 내장돼 있지 않다는 것, 프록시로 우회하는 방법
- [프로그래밍 초식 : DB 커넥션 풀 설정](https://velog.io/@atoye1/%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D-%EC%B4%88%EC%8B%9D-DB-%EC%BB%A4%EB%84%A5%EC%85%98-%ED%92%80-%EC%84%A4%EC%A0%95) — velog. 풀 크기 계산, 대기 시간은 짧게, 수명은 DB 타임아웃보다 짧게
- ['Connection has passed maxlifetime' 트러블 슈팅](https://velog.io/@hihello/Connection-has-passed-maxlifetime-%ED%8A%B8%EB%9F%AC%EB%B8%94-%EC%8A%88%ED%8C%85) — velog. HikariCP maxLifetime이 wait_timeout보다 길 때 생기는 문제
- [HikariCP Dead lock에서 벗어나기 (이론편)](https://techblog.woowahan.com/2664/) — 우아한형제들 기술블로그. 한 작업이 커넥션을 둘 잡으면 풀이 멈추는 구조
- [\[Project Loom\] Virtual Thread에 봄(Spring)은 왔는가](https://tech.kakaopay.com/post/ro-spring-virtual-thread/) — 카카오페이 기술블로그. 요청을 제한 없이 받으면 병목이 커넥션 풀로 옮겨 가는 사례
