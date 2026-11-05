---
title: "06. PHP는 요청마다 DB에 붙는데, Go는 커넥션을 어떻게 관리할까? (sqlx와 커넥션 풀)"
date: 2026-11-04
tags: ["Go"]
---

# 06. PHP는 요청마다 DB에 붙는데, Go는 커넥션을 어떻게 관리할까? (sqlx와 커넥션 풀)

**Go 학습 · 06**

PHP-FPM에서는 요청이 끝나면 DB 커넥션도 같이 끊겨서 커넥션 관리를 따로 고민할 일이 별로 없었어요. Go 서버는 프로세스 하나가 계속 떠 있어서 이야기가 달라져요. 이 글에서는 작은 프로그램 하나를 만들어 두고, 거기에 풀 설정과 실험을 하나씩 붙여 가면서 `database/sql` 의 커넥션 풀이 어떻게 도는지 봐요. 예제는 Go 1.26, sqlx v1.4.0, go-sql-driver/mysql v1.10.1, 로컬 MySQL 9.2, PHP 7.4.33 에서 직접 돌려 본 결과예요.

| 항목 | 내용 |
|---|---|
| 궁금했던 것 | PHP는 요청마다 DB에 붙었다 끊는데, Go는 커넥션을 어떻게 관리해? |
| 한 줄 답 | Go는 프로세스에 `*sql.DB` 하나를 만들어 두고, 그 안의 커넥션 풀에서 커넥션을 빌렸다 돌려줘요. 요청마다 새로 붙지 않으니 빠르지만, 풀 크기와 수명은 우리가 직접 정해 줘야 해요. |
| 정리한 날 | 2026-11-04 (예제 도입 고침 2026-11-05) |
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

- **PHP-FPM**: 갈 때마다 자전거를 새로 사서 타고, 도착하면 버려요. 매번 사는 시간(TCP 연결, 인증)이 들고, 버린 자전거(끊긴 소켓)가 한동안 길가에 쌓여요.
- **Go**: 회사 앞에 공용 자전거 거치대가 있어요. 고루틴은 거치대에서 자전거를 빌려 타고, 다 쓰면 다시 꽂아 둬요. 거치대 크기(`SetMaxOpenConns`)보다 사람이 많으면 누가 반납할 때까지 줄 서서 기다려요.

### 버린 자전거가 정말 쌓일까?

**상황**: "버린 자전거"는 TCP의 TIME_WAIT 소켓이에요. TCP는 연결을 먼저 끊은 쪽에 소켓을 잠깐(macOS 기준 수십 초) 남겨 둬요. 요청마다 붙었다 끊으면 그만큼 쌓일 거예요.

**해 본 것**: 로컬 MySQL에 "요청 100번"을 세 가지 방식으로 흉내 냈어요. 그리고 MySQL 포트 쪽에 남은 TIME_WAIT 소켓 수를 셌어요.

1. PHP 7.4 `mysqli` 로 연결하고 쿼리하고 닫기를 100번 해요. PHP-FPM 요청 100번과 같은 모양이에요.
1. Go에서 `sql.Open` 과 `Close` 를 100번 해요. 풀을 잘못 쓰는 모양이에요.
1. Go에서 `*sql.DB` 하나를 만들어 두고 `Ping` 을 100번 해요. 풀을 제대로 쓰는 모양이에요.

**결과**: 아래처럼 나왔어요. 셋째 줄만 TIME_WAIT가 거의 없어요.

```
PHP 7.4 mysqli, 요청마다 연결·종료 100번   → TIME_WAIT 119개 (시작할 때 15개)
Go, 요청마다 sql.Open·Close 100번         → TIME_WAIT 105개, 새 연결 100번
Go, *sql.DB 하나로 Ping 100번             → TIME_WAIT 2개,   새 연결 1번   ← 풀을 쓰면 이래요
```

**왜**: TIME_WAIT는 연결을 먼저 끊은 클라이언트 쪽(PHP 서버)에 쌓여요. 트래픽이 많으면 로컬 포트가 모자라서 새 연결이 실패할 수도 있어요. PHP에서는 이걸 피하려고 `mysqli` 의 `p:` 접두어나 `PDO::ATTR_PERSISTENT` 로 지속 연결을 쓰기도 했죠. 그런데 지속 연결은 워커마다 하나씩 붙잡고 있는 방식이라, 워커 수 × 서버 수만큼 MariaDB 커넥션이 늘 열려 있어요. 놀고 있는 워커도 커넥션을 쥐고 있어요.

Go 풀은 둘의 중간이에요. 재사용해서 TIME_WAIT가 거의 안 생기고, 최대 개수를 정해 두니 MariaDB 커넥션 수도 예측할 수 있어요. 둘째 줄처럼 Go라도 요청마다 `sql.Open` 을 하면 PHP와 똑같아져요(09장).

## 03. 만들어 볼 것: 풀 하나로 users 테이블 다루기

이제부터 나오는 코드는 모두 `main.go` 파일 하나에 들어 있어요. 풀을 만드는 `openDB` 와 풀 상태를 찍는 `printStats` 를 먼저 만들고, 장마다 함수를 하나씩 붙여요. 붙인 함수는 `go run . 이름` 으로 골라서 돌려요.

### 준비

#### 1. 로컬 MySQL을 띄워요

Homebrew로 설치한 MySQL 9.2를 33061 포트로 따로 띄웠어요. 평소 쓰는 DB와 섞이지 않게 하려고요. MariaDB가 손에 없어서 MySQL로 돌렸어요(10장 끝 참고).

#### 2. 테이블 두 개를 만들어요

사용자(`users`)와 글(`posts`)이에요. `nickname` 은 일부러 NULL을 허용했어요. NULL을 Go에서 어떻게 받는지 보려고요.

#### 3. Go 모듈을 만들고 라이브러리를 받아요

sqlx와 MySQL 드라이버 두 개만 있으면 돼요.

테이블은 이렇게 만들었어요. 앱이 쓸 계정 `app` 도 같이 만들어요.

```
CREATE DATABASE app;
CREATE USER 'app'@'%' IDENTIFIED BY 'pass';
GRANT ALL ON app.* TO 'app'@'%';

CREATE TABLE app.users (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(50) NOT NULL,
  nickname   VARCHAR(50) NULL,                       -- NULL 가능
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE app.posts (
  id      BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  title   VARCHAR(100) NOT NULL
);
```

Go 쪽은 composer로 패키지를 받는 것과 비슷해요. `go mod init` 이 `composer init`, `go get` 이 `composer require` 자리예요.

```bash
$ mkdir pool06 && cd pool06
$ go mod init pool06
$ go get github.com/jmoiron/sqlx@v1.4.0 github.com/go-sql-driver/mysql@v1.10.1
```

### 첫 코드: 풀을 만들고 상태 찍기

뼈대는 세 덩어리예요. 풀을 만드는 `openDB`, 풀 상태를 한 줄로 찍는 `printStats`, 그리고 둘을 부르는 `main` 이에요. `openDB` 안의 풀 설정 네 줄은 04장에서 하나씩 봐요. 지금은 `main` 이 `openDB` 를 **딱 한 번** 부른다는 것만 보면 돼요.

```go
import (
    _ "github.com/go-sql-driver/mysql" // import만 해 두면 "mysql" 이름으로 등록돼요
    "github.com/jmoiron/sqlx"
)

const dsn = "app:pass@tcp(127.0.0.1:33061)/app?parseTime=true&loc=UTC"

func printStats(label string, db *sqlx.DB) {
    s := db.Stats()
    fmt.Printf("%s: Open=%d InUse=%d Idle=%d WaitCount=%d WaitDuration=%s\n",
        label, s.OpenConnections, s.InUse, s.Idle, s.WaitCount, s.WaitDuration.Round(time.Millisecond))
}

func main() {
    ctx := context.Background()
    db, err := openDB(ctx)
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()
    printStats("연결 직후", db)

    exp := "basic"
    if len(os.Args) > 1 {
        exp = os.Args[1]
    }
    switch exp {
    case "basic":
        basic(ctx, db)
    case "idle":
        idleClosed(ctx)
    // ... 장마다 붙인 실험이 여기 이어져요
    }
}
```

`go run .` 으로 돌리면 첫 줄이 이렇게 나와요.

```bash
$ go run .
연결 직후: Open=1 InUse=0 Idle=1 WaitCount=0 WaitDuration=0s
```

`Open=1` 은 풀 안에 커넥션이 하나 생겼다는 뜻이에요. `openDB` 끝에서 부른 `Ping` 이 만든 거예요. `Idle=1` 은 그 커넥션이 지금 놀면서 거치대에 꽂혀 있다는 뜻이고요. 이 한 줄 모양을 기억해 두면 뒤의 실험 결과가 쉽게 읽혀요.

장마다 붙인 실험은 아래 이름으로 돌려요.

| 명령 | 무엇을 보나 | 장 |
|---|---|---|
| `go run . idle` | MaxIdleConns를 기본값으로 두면 커넥션을 몇 개나 버리나 | 04 |
| `go run . waittimeout` | DB가 먼저 끊은 커넥션을 풀이 어떻게 다루나 | 04 |
| `go run . stats` | 거치대가 2칸인데 4명이 오면 | 05 |
| `go run .` (basic) | sqlx Get, Select, NamedExec, In, 트랜잭션 | 06, 07 |
| `go run . timeout` | 쿼리에 1초 타임아웃을 걸면 | 07 |
| `go run . leak` / `leakfixed` | `rows.Close()` 를 빼먹으면, 고치면 | 09 |
| `go run . txapi` | 트랜잭션 안에서 느린 외부 API를 부르면 | 09 |

<details>
<summary>main.go 전체 코드 (이 글의 모든 실험이 들어 있어요)</summary>

```go
package main

import (
    "context"
    "database/sql"
    "errors"
    "fmt"
    "log"
    "os"
    "sync"
    "time"

    _ "github.com/go-sql-driver/mysql" // import만 해 두면 "mysql" 이름으로 등록돼요
    "github.com/jmoiron/sqlx"
)

const dsn = "app:pass@tcp(127.0.0.1:33061)/app?parseTime=true&loc=UTC"

type User struct {
    ID        int64          `db:"id"` // 컬럼 이름은 db 태그로 맞춰요
    Name      string         `db:"name"`
    Nickname  sql.NullString `db:"nickname"` // NULL 가능한 컬럼
    CreatedAt time.Time      `db:"created_at"`
}

type Post struct {
    ID     int64  `db:"id"`
    UserID int64  `db:"user_id"`
    Title  string `db:"title"`
}

// openDB 는 프로세스가 뜰 때 딱 한 번만 불러요
func openDB(ctx context.Context) (*sqlx.DB, error) {
    db, err := sqlx.Open("mysql", dsn)
    if err != nil {
        return nil, err
    }
    db.SetMaxOpenConns(20)                 // 동시에 열 수 있는 최대 개수
    db.SetMaxIdleConns(20)                 // 놀고 있어도 남겨 둘 개수
    db.SetConnMaxLifetime(5 * time.Minute) // 만든 지 이만큼 지나면 새로 바꿔요
    db.SetConnMaxIdleTime(2 * time.Minute) // 이만큼 놀았으면 닫아요

    if err := db.PingContext(ctx); err != nil { // Open은 실제로 연결을 안 해요
        db.Close()
        return nil, err
    }
    return db, nil
}

func printStats(label string, db *sqlx.DB) {
    s := db.Stats()
    fmt.Printf("%s: Open=%d InUse=%d Idle=%d WaitCount=%d WaitDuration=%s\n",
        label, s.OpenConnections, s.InUse, s.Idle, s.WaitCount, s.WaitDuration.Round(time.Millisecond))
}

func main() {
    ctx := context.Background()
    db, err := openDB(ctx)
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()
    printStats("연결 직후", db)

    exp := "basic"
    if len(os.Args) > 1 {
        exp = os.Args[1]
    }
    switch exp {
    case "basic":
        basic(ctx, db)
    case "idle":
        idleClosed(ctx)
    case "waittimeout":
        waitTimeout(ctx)
    case "stats":
        stats(ctx, db)
    case "timeout":
        timeout(ctx, db)
    case "leak":
        leak(ctx, db)
    case "leakfixed":
        leakFixed(ctx, db)
    case "txapi":
        txAPI(ctx, db)
    }
}

// ---- 05장: sqlx로 읽고 쓰기 ----

func basic(ctx context.Context, db *sqlx.DB) {
    db.MustExecContext(ctx, "TRUNCATE users") // 다시 돌려도 결과가 같게 비워요
    db.MustExecContext(ctx, "TRUNCATE posts")

    // 이름 붙은 파라미터: struct 필드를 :name 자리에 넣어 줘요
    for _, u := range []User{
        {Name: "진형", Nickname: sql.NullString{String: "jin", Valid: true}},
        {Name: "민수"}, // Nickname 은 NULL
    } {
        if _, err := db.NamedExecContext(ctx,
            `INSERT INTO users (name, nickname) VALUES (:name, :nickname)`, u); err != nil {
            log.Fatal(err)
        }
    }

    // 한 줄: Get
    var u User
    if err := db.GetContext(ctx, &u, "SELECT * FROM users WHERE id = ?", 1); err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Get: id=%d name=%s nickname=%v\n", u.ID, u.Name, u.Nickname)

    // 없는 id: Get 은 sql.ErrNoRows
    err := db.GetContext(ctx, &u, "SELECT * FROM users WHERE id = ?", 99)
    fmt.Println("Get(99):", errors.Is(err, sql.ErrNoRows))

    // 여러 줄: Select
    var users []User
    if err := db.SelectContext(ctx, &users, "SELECT * FROM users ORDER BY id"); err != nil {
        log.Fatal(err)
    }
    fmt.Println("Select:", len(users), "명")

    // 결과가 없으면 Select 는 에러 없이 nil 슬라이스
    var none []User
    err = db.SelectContext(ctx, &none, "SELECT * FROM users WHERE id > 100")
    fmt.Println("Select(없음):", err, none == nil)

    // 트랜잭션으로 사용자와 첫 글을 같이 넣어요
    if err := CreateUserWithPost(ctx, db, "지은", "첫 글"); err != nil {
        log.Fatal(err)
    }

    // IN 절: sqlx.In 이 슬라이스를 ?, ? 로 펼쳐 줘요
    q, args, err := sqlx.In("SELECT * FROM posts WHERE user_id IN (?)", []int64{1, 3})
    if err != nil {
        log.Fatal(err)
    }
    q = db.Rebind(q) // 드라이버에 맞는 자리표시자로
    fmt.Println("In:", q, args)
    var posts []Post
    if err := db.SelectContext(ctx, &posts, q, args...); err != nil {
        log.Fatal(err)
    }
    fmt.Printf("posts: %+v\n", posts)

    _, _, err = sqlx.In("SELECT * FROM posts WHERE user_id IN (?)", []int64{})
    fmt.Println("In(빈 슬라이스):", err)

    printStats("끝난 뒤", db)
}

// ---- 07장: 트랜잭션 ----

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

// ---- 04장 실험: MaxIdleConns 를 기본값(2)으로 두면 ----

func idleClosed(ctx context.Context) {
    for _, idle := range []int{2, 10} {
        db := sqlx.MustOpen("mysql", dsn)
        db.SetMaxOpenConns(10)
        db.SetMaxIdleConns(idle)
        for round := 0; round < 5; round++ { // 고루틴 10개가 동시에 쿼리하는 걸 5번
            var wg sync.WaitGroup
            for i := 0; i < 10; i++ {
                wg.Add(1)
                go func() {
                    defer wg.Done()
                    var x int
                    db.GetContext(ctx, &x, "SELECT SLEEP(0.1)")
                }()
            }
            wg.Wait()
        }
        fmt.Printf("MaxOpen=10 MaxIdle=%d → MaxIdleClosed=%d\n", idle, db.Stats().MaxIdleClosed)
        db.Close()
    }
}

// ---- 04장 실험: DB가 먼저 끊으면 ----

func waitTimeout(ctx context.Context) {
    for _, idleTime := range []time.Duration{0, time.Second} {
        db := sqlx.MustOpen("mysql", dsn+"&wait_timeout=2") // 이 커넥션은 2초 놀면 DB가 끊어요
        db.SetConnMaxIdleTime(idleTime)
        var id1, id2 int64
        db.GetContext(ctx, &id1, "SELECT CONNECTION_ID()")
        time.Sleep(3 * time.Second)
        err := db.GetContext(ctx, &id2, "SELECT CONNECTION_ID()")
        fmt.Printf("ConnMaxIdleTime=%s: 처음 ID=%d, 3초 뒤 ID=%d, err=%v, MaxIdleTimeClosed=%d\n",
            idleTime, id1, id2, err, db.Stats().MaxIdleTimeClosed)
        db.Close()
    }
}

// ---- 05장 실험: 거치대가 2칸인데 4명이 오면 ----

func stats(ctx context.Context, db *sqlx.DB) {
    db.SetMaxOpenConns(2)
    start := time.Now()
    var wg sync.WaitGroup
    for i := 0; i < 4; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            var x int
            db.GetContext(ctx, &x, "SELECT SLEEP(1)")
        }()
    }
    time.Sleep(500 * time.Millisecond)
    printStats("실행 중", db)
    wg.Wait()
    fmt.Println("걸린 시간:", time.Since(start).Round(100*time.Millisecond))
    printStats("끝난 뒤", db)
}

// ---- 07장 실험: 쿼리에 타임아웃 걸기 ----

func timeout(ctx context.Context, db *sqlx.DB) {
    ctx, cancel := context.WithTimeout(ctx, 1*time.Second)
    defer cancel()
    start := time.Now()
    var x int
    err := db.GetContext(ctx, &x, "SELECT SLEEP(3)")
    fmt.Println("결과:", err, "걸린 시간:", time.Since(start).Round(100*time.Millisecond))
    printStats("타임아웃 뒤", db)
}

// ---- 09장 실험: rows.Close() 를 빼먹으면 ----

func leak(ctx context.Context, db *sqlx.DB) {
    db.SetMaxOpenConns(2)
    for i := 0; i < 2; i++ {
        rows, err := db.QueryContext(ctx, "SELECT id FROM users")
        if err != nil {
            log.Fatal(err)
        }
        _ = rows // rows.Close() 를 빼먹었어요
    }
    printStats("두 번 빼먹은 뒤", db)

    ctx2, cancel := context.WithTimeout(ctx, 2*time.Second)
    defer cancel()
    start := time.Now()
    var x int
    err := db.GetContext(ctx2, &x, "SELECT 1")
    fmt.Println("세 번째 쿼리:", err, "기다린 시간:", time.Since(start).Round(100*time.Millisecond))
}

// 고친 쪽: 에러 확인 바로 다음 줄에 defer rows.Close()
func leakFixed(ctx context.Context, db *sqlx.DB) {
    db.SetMaxOpenConns(2)
    for i := 0; i < 100; i++ {
        func() {
            rows, err := db.QueryContext(ctx, "SELECT id FROM users")
            if err != nil {
                log.Fatal(err)
            }
            defer rows.Close()
            for rows.Next() {
            }
        }()
    }
    printStats("100번 돌린 뒤", db)
}

// ---- 09장 실험: 트랜잭션 안에서 느린 외부 API를 부르면 ----

func txAPI(ctx context.Context, db *sqlx.DB) {
    db.SetMaxOpenConns(2)
    var wg sync.WaitGroup
    for i := 0; i < 2; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            tx := db.MustBeginTx(ctx, nil)
            defer tx.Rollback()
            tx.MustExecContext(ctx, "INSERT INTO posts (user_id, title) VALUES (1, '알림 대기')")
            time.Sleep(2 * time.Second) // 외부 API 호출이 2초 걸린다고 쳐요
            tx.Commit()
        }()
    }
    time.Sleep(100 * time.Millisecond)

    ctx2, cancel := context.WithTimeout(ctx, 500*time.Millisecond)
    defer cancel()
    var x int
    err := db.GetContext(ctx2, &x, "SELECT 1") // 트랜잭션과 상관없는 쿼리
    fmt.Println("상관없는 SELECT 1:", err)
    wg.Wait()
}
```

</details>

## 04. 풀 설정 네 개 고르기

03장에서 미뤄 둔 `openDB` 를 열어 봐요. 풀을 만들고, 설정 네 개를 정하고, 실제로 붙는지 `Ping` 으로 확인해요. 눈여겨볼 곳은 `Set...` 네 줄이에요.

```go
// openDB 는 프로세스가 뜰 때 딱 한 번만 불러요
func openDB(ctx context.Context) (*sqlx.DB, error) {
    db, err := sqlx.Open("mysql", dsn)
    if err != nil {
        return nil, err
    }
    db.SetMaxOpenConns(20)                 // 동시에 열 수 있는 최대 개수
    db.SetMaxIdleConns(20)                 // 놀고 있어도 남겨 둘 개수
    db.SetConnMaxLifetime(5 * time.Minute) // 만든 지 이만큼 지나면 새로 바꿔요
    db.SetConnMaxIdleTime(2 * time.Minute) // 이만큼 놀았으면 닫아요

    if err := db.PingContext(ctx); err != nil { // Open은 실제로 연결을 안 해요
        db.Close()
        return nil, err
    }
    return db, nil
}
```

네 설정을 빼면 모두 기본값으로 돌아요. 기본값과 고르는 방법은 이래요.

| 설정 | 기본값 | 어떻게 고를까 |
|---|---|---|
| `SetMaxOpenConns` | 0 (무제한) | **꼭 정해요.** 무제한이면 고루틴이 몰릴 때 커넥션도 끝없이 늘어서 MariaDB `max_connections` 에 부딪혀요. 파드 수까지 곱해서 계산해요(09장). |
| `SetMaxIdleConns` | 2 | 보통 MaxOpen이랑 같게 둬요. 기본값 2로 두면 바쁠 때 열었던 커넥션을 반납하자마자 닫아 버려서, 결국 PHP처럼 붙었다 끊기를 반복해요. |
| `SetConnMaxLifetime` | 0 (영원히) | MariaDB `wait_timeout` 이나 중간 L4, 방화벽의 유휴 타임아웃보다 **확실히 짧게** 잡아요. 드라이버 README는 5분 이하를 권해요. |
| `SetConnMaxIdleTime` | 0 (영원히) | 트래픽이 빠진 뒤 놀고 있는 커넥션을 정리해요. 새벽에 MariaDB 커넥션 수를 줄이고 싶을 때 써요. |

### 실험 1: MaxIdleConns를 기본값으로 두면 진짜 다시 붙을까?

**상황**: 표에서 "기본값 2로 두면 반납하자마자 닫는다"고 했어요. 바쁜 순간에 커넥션을 10개 열었다가, 쿼리가 끝나면 2개만 남기고 8개를 버린다는 뜻이에요.

**해 본 것**: MaxOpen을 10으로 두고, MaxIdle만 2와 10으로 바꿔 가며 같은 일을 시켰어요. 고루틴 10개가 0.1초짜리 쿼리를 동시에 날리는 걸 5번 반복해요. 끝나고 `Stats().MaxIdleClosed` 로 "놀 자리가 없어서 닫은 커넥션 수"를 봐요.

```go
func idleClosed(ctx context.Context) {
    for _, idle := range []int{2, 10} {
        db := sqlx.MustOpen("mysql", dsn)
        db.SetMaxOpenConns(10)
        db.SetMaxIdleConns(idle)
        for round := 0; round < 5; round++ { // 고루틴 10개가 동시에 쿼리하는 걸 5번
            var wg sync.WaitGroup
            for i := 0; i < 10; i++ {
                wg.Add(1)
                go func() {
                    defer wg.Done()
                    var x int
                    db.GetContext(ctx, &x, "SELECT SLEEP(0.1)")
                }()
            }
            wg.Wait()
        }
        fmt.Printf("MaxOpen=10 MaxIdle=%d → MaxIdleClosed=%d\n", idle, db.Stats().MaxIdleClosed)
        db.Close()
    }
}
```

**결과**: `go run . idle` 로 돌렸어요.

```
MaxOpen=10 MaxIdle=2 → MaxIdleClosed=40     ← 커넥션 40개를 열자마자 버렸어요
MaxOpen=10 MaxIdle=10 → MaxIdleClosed=0
```

**왜**: 한 번 돌 때마다 10개를 쓰고 2개만 남기니 8개씩 버려요. 다음 번에는 버린 8개를 다시 열어야 하고요. 8개 × 5번 = 40개예요. 둘을 같게 두면 한 번 연 10개를 계속 써서 0이에요.

### 실험 2: DB가 먼저 끊으면 풀은 알까?

**상황**: MariaDB는 `wait_timeout` (기본 28800초, 8시간) 동안 아무 쿼리도 없는 커넥션을 서버 쪽에서 먼저 끊어요. 풀은 그걸 모르고 그 커넥션을 계속 들고 있어요. 다음 쿼리가 끊긴 커넥션을 빌려 가면 어떻게 될까요?

**해 본 것**: 8시간을 기다릴 수는 없으니 DSN에 `wait_timeout=2` 를 붙였어요. 이 커넥션은 2초만 놀아도 DB가 끊어요. 커넥션 ID를 한 번 읽고, 3초 쉬었다가 다시 읽어요. 처음에는 풀 설정 없이, 다음에는 `SetConnMaxIdleTime(1초)` 를 걸고 돌려요.

```go
func waitTimeout(ctx context.Context) {
    for _, idleTime := range []time.Duration{0, time.Second} {
        db := sqlx.MustOpen("mysql", dsn+"&wait_timeout=2") // 이 커넥션은 2초 놀면 DB가 끊어요
        db.SetConnMaxIdleTime(idleTime)
        var id1, id2 int64
        db.GetContext(ctx, &id1, "SELECT CONNECTION_ID()")
        time.Sleep(3 * time.Second)
        err := db.GetContext(ctx, &id2, "SELECT CONNECTION_ID()")
        fmt.Printf("ConnMaxIdleTime=%s: 처음 ID=%d, 3초 뒤 ID=%d, err=%v, MaxIdleTimeClosed=%d\n",
            idleTime, id1, id2, err, db.Stats().MaxIdleTimeClosed)
        db.Close()
    }
}
```

**결과**: `go run . waittimeout` 결과예요. 첫 번째에만 드라이버 로그가 한 줄 찍혔어요.

```
[mysql] connection.go:803 closing bad idle connection: unexpected read from socket   ← 끊긴 걸 쓰려다 들켰어요
ConnMaxIdleTime=0s: 처음 ID=66, 3초 뒤 ID=67, err=<nil>, MaxIdleTimeClosed=0
ConnMaxIdleTime=1s: 처음 ID=68, 3초 뒤 ID=69, err=<nil>, MaxIdleTimeClosed=1   ← 로그 없이 풀이 먼저 정리했어요
```

**왜**: 두 번 다 커넥션 ID가 바뀌었어요. 끊긴 커넥션 대신 새로 붙었다는 뜻이에요. 첫 번째는 드라이버가 끊긴 커넥션을 꺼내 쓰려다 알아채고 버린 거예요. 이번엔 에러까지는 안 났지만, 쿼리 도중에 끊기면 `invalid connection` 에러로 올라올 수 있어요. 두 번째는 1초 놀았을 때 풀이 먼저 닫아서(`MaxIdleTimeClosed=1`) 끊긴 커넥션을 만날 일이 없었어요. 그래서 수명은 `wait_timeout` 보다 짧게 둬요.

## 05. `db.Stats()` 로 풀 들여다보기

03장에서 만든 `printStats` 가 부르는 `db.Stats()` 는 풀의 지금 상태를 알려 줘요. 공용 자전거 비유로 실험해 봐요.

**상황**: 거치대가 2칸인데 4명이 동시에 자전거를 빌리러 오면, 2명은 줄을 서야 해요.

**해 본 것**: 풀 크기를 2로 줄이고, 1초 걸리는 쿼리(`SELECT SLEEP(1)`)를 고루틴 4개가 동시에 날려요. 0.5초 뒤 한창 도는 중에 한 번, 다 끝나고 한 번 상태를 찍어요.

```go
func stats(ctx context.Context, db *sqlx.DB) {
    db.SetMaxOpenConns(2)
    start := time.Now()
    var wg sync.WaitGroup
    for i := 0; i < 4; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            var x int
            db.GetContext(ctx, &x, "SELECT SLEEP(1)")
        }()
    }
    time.Sleep(500 * time.Millisecond)
    printStats("실행 중", db)
    wg.Wait()
    fmt.Println("걸린 시간:", time.Since(start).Round(100*time.Millisecond))
    printStats("끝난 뒤", db)
}
```

**결과**: `go run . stats` 결과예요.

```
실행 중: Open=2 InUse=2 Idle=0 WaitCount=2 WaitDuration=0s       ← 2명은 타고, 2명은 줄 서 있어요
걸린 시간: 2s
끝난 뒤: Open=2 InUse=0 Idle=2 WaitCount=2 WaitDuration=2.011s
```

**왜**: 앞의 두 고루틴이 1초 동안 커넥션을 쓰고, 나머지 둘은 반납을 기다렸다가 1초 더 써요. 그래서 1초짜리 쿼리 4개가 2초 걸렸어요. 각 숫자는 이런 뜻이에요.

- **InUse / Idle**: 빌려 간 개수랑 거치대에 꽂혀 있는 개수예요.
- **WaitCount, WaitDuration**: 커넥션이 없어서 줄 선 횟수랑 기다린 시간의 합이에요. 2명이 1초씩 기다려서 약 2초예요. 이 숫자가 계속 오르면 풀이 작거나 커넥션을 오래 붙잡는 코드가 있다는 신호예요(09장).
- **MaxIdleClosed, MaxIdleTimeClosed, MaxLifetimeClosed**: 설정 때문에 닫힌 개수예요. 04장 실험에서 본 것처럼 MaxIdleClosed가 빠르게 오르면 MaxIdleConns가 너무 작아요.

## 06. sqlx가 더해 주는 것

sqlx는 `database/sql` 을 감싼 얇은 라이브러리예요. ORM이 아니라 SQL은 그대로 직접 쓰고, **결과를 struct에 담는 귀찮은 일**만 줄여 줘요. 커넥션 풀도 `database/sql` 것을 그대로 써요. CodeIgniter 4로 치면 Query Builder 없이 `$db->query($sql)->getResult()` 만 쓰는 느낌이에요.

먼저 03장에서 만든 `users` 테이블의 한 줄을 담을 struct를 만들어요. 컬럼 이름은 `db` 태그로 맞추고, NULL이 올 수 있는 `nickname` 은 `sql.NullString` 으로 받아요.

```
type User struct {
    ID        int64          `db:"id"` // 컬럼 이름은 db 태그로 맞춰요
    Name      string         `db:"name"`
    Nickname  sql.NullString `db:"nickname"` // NULL 가능한 컬럼
    CreatedAt time.Time      `db:"created_at"`
}
```

이제 `basic` 함수에서 이 struct로 쓰고 읽어요. 사용자 둘을 넣고(`NamedExec`), 한 명을 읽고(`Get`), 없는 사람을 읽고, 전부 읽어요(`Select`). 아래는 `basic` 에서 sqlx를 쓰는 부분만 잘라 온 거예요.

```go
// 이름 붙은 파라미터: struct 필드를 :name 자리에 넣어 줘요
for _, u := range []User{
    {Name: "진형", Nickname: sql.NullString{String: "jin", Valid: true}},
    {Name: "민수"}, // Nickname 은 NULL
} {
    if _, err := db.NamedExecContext(ctx,
        `INSERT INTO users (name, nickname) VALUES (:name, :nickname)`, u); err != nil {
        log.Fatal(err)
    }
}

// 한 줄: Get
var u User
if err := db.GetContext(ctx, &u, "SELECT * FROM users WHERE id = ?", 1); err != nil {
    log.Fatal(err)
}
fmt.Printf("Get: id=%d name=%s nickname=%v\n", u.ID, u.Name, u.Nickname)

// 없는 id: Get 은 sql.ErrNoRows
err := db.GetContext(ctx, &u, "SELECT * FROM users WHERE id = ?", 99)
fmt.Println("Get(99):", errors.Is(err, sql.ErrNoRows))

// 여러 줄: Select
var users []User
if err := db.SelectContext(ctx, &users, "SELECT * FROM users ORDER BY id"); err != nil {
    log.Fatal(err)
}
fmt.Println("Select:", len(users), "명")

// 결과가 없으면 Select 는 에러 없이 nil 슬라이스
var none []User
err = db.SelectContext(ctx, &none, "SELECT * FROM users WHERE id > 100")
fmt.Println("Select(없음):", err, none == nil)
```

IN 절은 `sqlx.In` 이 맡아요. 슬라이스를 넘기면 `?` 를 개수만큼 펼쳐 줘요. 이 부분은 07장의 트랜잭션으로 글을 하나 넣은 다음에 돌아요.

```go
// IN 절: sqlx.In 이 슬라이스를 ?, ? 로 펼쳐 줘요
q, args, err := sqlx.In("SELECT * FROM posts WHERE user_id IN (?)", []int64{1, 3})
if err != nil {
    log.Fatal(err)
}
q = db.Rebind(q) // 드라이버에 맞는 자리표시자로
fmt.Println("In:", q, args)
var posts []Post
if err := db.SelectContext(ctx, &posts, q, args...); err != nil {
    log.Fatal(err)
}
fmt.Printf("posts: %+v\n", posts)

_, _, err = sqlx.In("SELECT * FROM posts WHERE user_id IN (?)", []int64{})
fmt.Println("In(빈 슬라이스):", err)
```

`go run .` 으로 `basic` 을 돌린 결과예요.

```
Get: id=1 name=진형 nickname={jin true}           ← NullString 은 {값 Valid} 로 찍혀요
Get(99): true                                    ← 없으면 sql.ErrNoRows
Select: 2 명
Select(없음): <nil> true                         ← 에러 없이 nil 슬라이스
In: SELECT * FROM posts WHERE user_id IN (?, ?) [1 3]
posts: [{ID:1 UserID:3 Title:첫 글}]
In(빈 슬라이스): empty slice passed to 'in' query   ← 빈 목록은 에러
끝난 뒤: Open=1 InUse=0 Idle=1 WaitCount=0 WaitDuration=0s
```

볼 곳은 세 군데예요. `Get` 은 결과가 없으면 에러를 주고, `Select` 는 에러 없이 빈 슬라이스를 줘요. 둘이 다르게 굴어요. **빈 슬라이스를 `sqlx.In` 에 넘기면 에러**가 나니 목록이 비었으면 쿼리 전에 미리 빠져나와요. 마지막 줄의 `Open=1` 도 봐 둘 만해요. 쿼리를 여러 번 했지만 커넥션 하나로 다 했어요.

`database/sql` 만 쓰면 `rows.Next()` 를 돌면서 `rows.Scan(&u.ID, &u.Name, ...)` 를 컬럼 순서대로 직접 써야 해요. sqlx는 이걸 태그로 해결해 줘요.

## 07. 트랜잭션과 타임아웃

### 트랜잭션: BeginTxx, defer Rollback, ctx 넘기기

06장의 `basic` 에서 "사용자 지은과 첫 글"을 같이 넣을 때 부른 함수예요. 사용자를 넣고 받은 id로 글을 넣어요. 둘 중 하나만 들어가면 안 되니 트랜잭션으로 묶어요. `defer tx.Rollback()` 이 어디 붙어 있는지 보세요.

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

06장 결과의 `posts: [{ID:1 UserID:3 Title:첫 글}]` 가 이 함수가 넣은 글이에요. 지은이 세 번째 사용자라 `UserID:3` 이에요.

- **트랜잭션은 커넥션 하나를 통째로 빌려 가요.** `Commit` 이나 `Rollback` 을 할 때까지 그 커넥션은 풀로 안 돌아와요.
- **`defer tx.Rollback()` 을 바로 붙여요.** 중간에 `return err` 로 빠져나가도 롤백되고 커넥션이 돌아와요. 두 번째 INSERT 전에 에러를 내 봤더니 첫 INSERT도 남지 않았어요.
- **안에서는 꼭 `tx.` 로 쿼리해요.** 실수로 `db.ExecContext` 를 부르면 풀에서 다른 커넥션을 빌려서 트랜잭션 밖에서 실행돼요.
- **ctx를 넘겨요.** 요청이 취소되거나 타임아웃이 나면 `database/sql` 이 트랜잭션을 알아서 롤백해요.

### 쿼리에 타임아웃 걸기

**상황**: 느린 쿼리 하나가 커넥션을 오래 붙잡으면 다른 요청이 줄을 서요(05장). 기다리는 시간에 상한을 두고 싶어요.

**해 본 것**: ctx에 1초 타임아웃을 걸고 3초 걸리는 쿼리를 날려요. 그리고 풀 상태를 찍어요.

```go
func timeout(ctx context.Context, db *sqlx.DB) {
    ctx, cancel := context.WithTimeout(ctx, 1*time.Second)
    defer cancel()
    start := time.Now()
    var x int
    err := db.GetContext(ctx, &x, "SELECT SLEEP(3)")
    fmt.Println("결과:", err, "걸린 시간:", time.Since(start).Round(100*time.Millisecond))
    printStats("타임아웃 뒤", db)
}
```

**결과**: `go run . timeout` 결과예요.

```
연결 직후: Open=1 InUse=0 Idle=1 WaitCount=0 WaitDuration=0s
결과: context deadline exceeded 걸린 시간: 1s
타임아웃 뒤: Open=0 InUse=0 Idle=0 WaitCount=0 WaitDuration=0s   ← 커넥션이 하나 줄었어요
```

**왜**: 3초를 다 기다리지 않고 1초 만에 에러로 돌아왔어요. 눈여겨볼 건 `Open` 이 1에서 0이 된 거예요. 드라이버는 쿼리 중간에 끊긴 커넥션을 재사용하지 않고 버려요. 타임아웃이 자주 나면 풀이 커넥션을 계속 새로 만들게 돼요. 반대로 ctx 타임아웃을 안 걸면 느린 쿼리가 커넥션을 끝까지 붙잡아요.

## 08. PHP, 스프링과 비교

지금까지 본 것을 PHP-FPM, 스프링과 나란히 놓으면 이래요.

| 궁금한 것 | PHP-FPM (CI4) | Go (sqlx) | 스프링 (HikariCP) |
|---|---|---|---|
| 커넥션은 언제 생겨? | 요청마다 연결, 끝나면 종료 | 필요할 때 풀이 만들고 재사용 | 뜰 때 minimumIdle만큼 미리 만들어요 |
| 최대 개수 | `pm.max_children` 가 사실상 상한 | `SetMaxOpenConns` (기본 무제한) | `maximumPoolSize` (기본 10) |
| 커넥션 수명 | 요청 하나 | `SetConnMaxLifetime` (기본 무한) | `maxLifetime` (기본 30분) |
| 풀이 다 찼을 때 | 해당 없음 | ctx가 끝날 때까지 기다려요 | `connectionTimeout` (기본 30초) 뒤 예외 |
| 트랜잭션 전달 | `$db->transStart()` | `tx` 를 인자로 직접 넘겨요 | `@Transactional` + ThreadLocal |
| 결과 매핑 | `getResultArray()` | `db` 태그 + Get/Select | JPA, MyBatis |

HikariCP를 써 봤다면 설정 고민은 그대로 가져오면 돼요. `maxLifetime` 을 DB 타임아웃보다 몇 초 짧게 두라는 HikariCP 권고는 Go의 `SetConnMaxLifetime` 에도 똑같이 적용돼요. 다른 점은 Go에는 "풀 대기 타임아웃" 설정이 따로 없다는 거예요. 기다리는 시간은 ctx의 타임아웃이 대신 정해요. ctx 없이 `db.Query` 를 부르면 커넥션이 날 때까지 무한정 기다려요.

## 09. 조심할 것

운영에서 풀이 막히는 원인 두 가지는 직접 재현해 봤어요. 둘 다 05장의 "거치대 2칸" 조건에서 돌렸어요.

### 실험 3: `rows.Close()` 를 빼먹으면

**상황**: sqlx의 `Get`, `Select` 는 결과를 다 읽고 알아서 닫아 줘요. 그런데 `db.QueryContext` 로 받은 rows는 직접 닫아야 해요. 안 닫으면 그 커넥션은 계속 "빌려 간" 상태로 남아요.

**해 본 것**: 풀 크기 2에서 rows를 두 번 받고 닫지 않았어요. 그다음 상관없는 `SELECT 1` 을 2초 타임아웃으로 날려요.

```go
func leak(ctx context.Context, db *sqlx.DB) {
    db.SetMaxOpenConns(2)
    for i := 0; i < 2; i++ {
        rows, err := db.QueryContext(ctx, "SELECT id FROM users")
        if err != nil {
            log.Fatal(err)
        }
        _ = rows // rows.Close() 를 빼먹었어요
    }
    printStats("두 번 빼먹은 뒤", db)

    ctx2, cancel := context.WithTimeout(ctx, 2*time.Second)
    defer cancel()
    start := time.Now()
    var x int
    err := db.GetContext(ctx2, &x, "SELECT 1")
    fmt.Println("세 번째 쿼리:", err, "기다린 시간:", time.Since(start).Round(100*time.Millisecond))
}
```

**결과**: `go run . leak` 결과예요.

```
두 번 빼먹은 뒤: Open=2 InUse=2 Idle=0 WaitCount=0 WaitDuration=0s   ← 두 칸 다 빌려 간 채로 멈췄어요
세 번째 쿼리: context deadline exceeded 기다린 시간: 2s
```

고친 쪽(`leakFixed`)은 에러 확인 바로 다음 줄에 `defer rows.Close()` 를 붙이고 같은 조건에서 100번 돌렸어요. `go run . leakfixed` 결과는 이래요.

```
100번 돌린 뒤: Open=1 InUse=0 Idle=1 WaitCount=0 WaitDuration=0s   ← 커넥션 하나로 100번 다 했어요
```

**왜**: 거치대 2칸이 모두 반납 안 된 자전거로 차 있어서 세 번째 사람은 타임아웃까지 줄만 섰어요. ctx 타임아웃이 없었다면 영원히 기다렸을 거예요(08장).

### 실험 4: 트랜잭션 안에서 느린 외부 API를 부르면

**상황**: 글을 저장하는 트랜잭션 안에서 알림 API를 부른다고 해 봐요. 트랜잭션은 커넥션을 통째로 빌려 가니(07장), API가 느리면 그동안 커넥션도 같이 묶여요.

**해 본 것**: 풀 크기 2에서 트랜잭션 2개가 INSERT를 하고 2초짜리 "외부 호출"(`time.Sleep`)을 해요. 그사이 트랜잭션과 상관없는 `SELECT 1` 을 0.5초 타임아웃으로 날려요.

```go
func txAPI(ctx context.Context, db *sqlx.DB) {
    db.SetMaxOpenConns(2)
    var wg sync.WaitGroup
    for i := 0; i < 2; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            tx := db.MustBeginTx(ctx, nil)
            defer tx.Rollback()
            tx.MustExecContext(ctx, "INSERT INTO posts (user_id, title) VALUES (1, '알림 대기')")
            time.Sleep(2 * time.Second) // 외부 API 호출이 2초 걸린다고 쳐요
            tx.Commit()
        }()
    }
    time.Sleep(100 * time.Millisecond)

    ctx2, cancel := context.WithTimeout(ctx, 500*time.Millisecond)
    defer cancel()
    var x int
    err := db.GetContext(ctx2, &x, "SELECT 1") // 트랜잭션과 상관없는 쿼리
    fmt.Println("상관없는 SELECT 1:", err)
    wg.Wait()
}
```

**결과**: `go run . txapi` 결과예요.

```
상관없는 SELECT 1: context deadline exceeded   ← DB는 한가한데 커넥션이 없어서 실패했어요
```

**왜**: DB는 2초 동안 아무 일도 안 했어요. 커넥션만 트랜잭션에 묶여 있었어요. 외부 호출은 트랜잭션 밖으로 빼요. 먼저 호출하고, 결과를 들고 짧게 커밋해요.

### 그 밖에 조심할 것

| 조심할 것 | 왜 문제가 되는데? | 어떻게 해? |
|---|---|---|
| **`rows.Close()` 를 빼먹어요** | 위 실험 3처럼 커넥션이 풀로 안 돌아와요. 두 번 빼먹으니 `InUse=2` 로 고정되고 세 번째 쿼리가 2초 뒤 타임아웃이 났어요. | 에러 확인 바로 다음 줄에 `defer rows.Close()`. sqlx Get/Select는 알아서 닫아 줘요. |
| **`sql.ErrNoRows`** | Get은 결과가 없으면 에러를 돌려줘요. Select는 에러 없이 빈 슬라이스(`nil`)예요. 06장 결과처럼 둘이 달라요. | `errors.Is(err, sql.ErrNoRows)` 로 골라서 404 같은 걸로 바꿔요. `nil` 슬라이스는 JSON에서 `null` 이 되니 03편도 같이 봐요. |
| **NULL 컬럼** | NULL을 `string` 에 담으면 `converting NULL to string is unsupported` 에러가 나요. PHP는 그냥 `null` 을 줬죠. | `sql.NullString` (Valid로 확인) 이나 `*string` (nil로 확인)을 써요. 응답 JSON까지 생각하면 포인터가 편해요. |
| **`parseTime=true` 가 없어요** | DATETIME이 `[]byte` 로 와서 `time.Time` 에 못 담아요(`unsupported Scan, storing driver.Value type []uint8`). | DSN에 `parseTime=true` 를 붙여요. DATETIME에는 시간대가 없으니 `loc` 도 명시해요(03장의 `dsn`). |
| **요청마다 `sql.Open`** | 풀을 매번 새로 만들고 버리는 거라 PHP보다 나쁠 수도 있어요. 02장에서 100번 해 보니 새 연결 100번, TIME_WAIT 105개였어요. | main에서 한 번 만들고 의존성으로 넘겨요. 테스트 코드도 마찬가지예요. |
| **트랜잭션 안에서 외부 API 호출** | 위 실험 4처럼 API가 느린 동안 커넥션을 쥐고 있어서, 상관없는 쿼리까지 실패해요. | 외부 호출은 트랜잭션 밖으로 빼요. 먼저 호출하고 결과를 들고 짧게 커밋해요. |
| **MaxOpenConns × 파드 수** | MaxOpen 20, 파드 10개면 최대 200개예요. MariaDB 기본 `max_connections` 는 151이에요. 롤링 배포 중엔 파드가 잠깐 더 늘어요. | (파드 최대 수 × MaxOpen) + 배치, 관리 도구 몫이 `max_connections` 안에 들어오게 잡아요. |

## 10. 스스로 확인해 보기

#### 1. 게시글 목록 API가 평소엔 빠른데, 하루에 몇 번 모든 API가 같이 느려져요. `db.Stats()` 를 보니 `InUse` 가 MaxOpen에 붙어 있고 `WaitCount` 가 계속 올라요. 뭘 먼저 의심할까?

<details>
<summary>답 보기</summary>

커넥션을 오래 쥐고 있는 코드를 먼저 찾아요. 1순위는 `rows.Close()` 를 빼먹은 곳(실험 3), 2순위는 트랜잭션 안에서 외부 API나 파일 처리를 하는 곳(실험 4), 3순위는 타임아웃 없는 느린 쿼리예요. 풀 크기를 키우는 건 원인을 없앤 다음에 해요. 먼저 키우면 MariaDB `max_connections` 에 대신 부딪혀요.

</details>

#### 2. 서버를 띄우고 밤새 트래픽이 없다가, 아침 첫 요청에서 `invalid connection` 이 한 번 났어요. MariaDB `wait_timeout` 은 600초고 풀 설정은 MaxOpen만 했어요. 왜일까?

<details>
<summary>답 보기</summary>

`SetConnMaxLifetime`, `SetConnMaxIdleTime` 이 기본값(무한)이라 풀이 밤새 커넥션을 들고 있었어요. 그사이 MariaDB가 600초 지난 커넥션을 먼저 끊었어요. 04장 실험 2의 첫 번째 경우예요. 수명을 `wait_timeout` 보다 짧게(예: 5분 미만) 두면 풀이 먼저 정리해요.

</details>

이 글의 예제는 로컬 MySQL 9.2로 돌렸어요. MariaDB에서 직접 돌려 보지는 않았어요. 같은 드라이버와 같은 프로토콜이라 결과는 같을 거라고 보지만, 확인한 건 아니에요. 04장 표의 풀 숫자(20, 5분, 2분)와 09장의 파드 계산은 실행한 게 아니라 예시예요.

## 11. 참고한 글

- [\[Go\] MySQL 연결해보기](https://velog.io/@flfns333/Go-MySQL-%EC%97%B0%EA%B2%B0%ED%95%B4%EB%B3%B4%EA%B8%B0): velog. MaxIdleConns를 MaxOpenConns와 같게, ConnMaxLifetime 5분 미만, parseTime
- [PHP Connection Pool](https://velog.io/@woooooooong/PHP-Connection-Pool): velog. PHP에는 커넥션 풀이 내장돼 있지 않다는 것, 프록시로 우회하는 방법
- [프로그래밍 초식 : DB 커넥션 풀 설정](https://velog.io/@atoye1/%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D-%EC%B4%88%EC%8B%9D-DB-%EC%BB%A4%EB%84%A5%EC%85%98-%ED%92%80-%EC%84%A4%EC%A0%95): velog. 풀 크기 계산, 대기 시간은 짧게, 수명은 DB 타임아웃보다 짧게
- ['Connection has passed maxlifetime' 트러블 슈팅](https://velog.io/@hihello/Connection-has-passed-maxlifetime-%ED%8A%B8%EB%9F%AC%EB%B8%94-%EC%8A%88%ED%8C%85): velog. HikariCP maxLifetime이 wait_timeout보다 길 때 생기는 문제
- [HikariCP Dead lock에서 벗어나기 (이론편)](https://techblog.woowahan.com/2664/): 우아한형제들 기술블로그. 한 작업이 커넥션을 둘 잡으면 풀이 멈추는 구조
- [\[Project Loom\] Virtual Thread에 봄(Spring)은 왔는가](https://tech.kakaopay.com/post/ro-spring-virtual-thread/): 카카오페이 기술블로그. 요청을 제한 없이 받으면 병목이 커넥션 풀로 옮겨 가는 사례
