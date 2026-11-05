---
title: "07. Go에서는 테스트를 왜 표로 짤까? (table-driven test)"
date: 2026-11-04
tags: ["Go"]
---

# 07. Go에서는 테스트를 왜 표로 짤까? (table-driven test)

**Go 학습 · 07**

Go 테스트 코드를 열어 보면 거의 다 `tests := []struct{...}` 로 시작해요. PHPUnit의 `@dataProvider` 나 JUnit의 `@ParameterizedTest` 를 써 봤다면 금방 익숙해지는데, Go에는 어노테이션이 없어서 모양이 꽤 달라 보여요. 이 글에서는 제목을 URL 조각으로 바꾸는 작은 함수 하나를 만들고, 그 테스트를 `if` 몇 줄에서 시작해 표로 키워 가요. 정상/실패/경계값으로 나누는 법, 병렬 실행할 때 걸리는 곳까지 같은 예제로 이어서 봐요. 예제는 전부 Go 1.26에서 직접 돌려 본 결과예요.

| 항목 | 내용 |
|---|---|
| 궁금했던 것 | Go 테스트는 왜 다 표(struct 슬라이스)로 짜? |
| 한 줄 답 | Go에는 `@dataProvider` 같은 어노테이션이 없어서, 테스트 케이스를 struct 슬라이스로 적고 for문과 `t.Run` 으로 돌리는 게 그 역할을 해요. 케이스 추가가 표에 한 줄 넣는 걸로 끝나요. |
| 정리한 날 | 2026-11-04 |
| 같이 볼 글 | Go 학습 내용 · [02. goroutine](02-goroutine-spring.md) · [03. PHP 7.4와 문법 차이](03-php-문법차이.md) · [05. gin으로 API 만들기](05-gin-api.md) |

## 01. 한 줄 답: 어노테이션 대신 "표 + for문"이에요

시험 채점을 떠올리면 쉬워요. 문제마다 채점 방법을 새로 만들지 않고, 문제와 정답을 표에 쭉 적어 둔 다음 채점하는 사람 한 명이 위에서부터 맞춰 보잖아요. table-driven test가 딱 그거예요. **표 = 테스트 케이스 목록**, **for문 + `t.Run` = 채점하는 사람**이에요.

> 💡 PHPUnit은 프레임워크가 `@dataProvider` 를 읽고 케이스를 돌려 줘요. Go는 그 일을 우리가 for문으로 직접 해요. 마법이 없어서 처음엔 길어 보이는데, 읽을 때 숨은 게 없어요.

> 📌 기본 도구\
> **`testing` 하나**\
> assert 함수가 없어요. `if got != want { t.Errorf(...) }` 를 직접 써요.

> 📌 핵심 패턴\
> **struct 슬라이스 + `t.Run`**\
> 케이스마다 이름이 붙은 서브테스트가 생겨서, 뭐가 깨졌는지 바로 보여요.

> 📌 조심할 곳\
> **병렬 실행**\
> `t.Parallel()` 을 붙이면 케이스끼리 공유하는 값에서 레이스가 나요.

## 02. 만들어 볼 것: 제목을 URL 조각으로 바꾸는 `Slug`

블로그 글 주소가 `/posts/hello-world` 처럼 생긴 거 많이 보셨죠? 제목에서 그 `hello-world` 부분을 만드는 함수를 하나 짜고, 이 글 내내 이 함수를 테스트해요. 규칙은 이래요.

| 넣는 값 | 나오는 값 | 규칙 |
|---|---|---|
| `"Hello World"` | `"hello-world"` | 소문자로 바꾸고, 공백은 `-` |
| `"Go 테스트 입문"` | `"go-테스트-입문"` | 한글도 글자라서 그대로 둬요 |
| `"a!!!b"` | `"a-b"` | 글자·숫자가 아닌 게 이어지면 `-` 하나로 |
| `""`, `" "` | `ErrEmpty` | 남는 글자가 없으면 에러 |
| 81자 이상 | `ErrTooLong` | 80자까지만 받아요 |

폴더 하나에 파일 두 개를 둬요. Go는 테스트 파일을 따로 `tests/` 폴더에 모으지 않고, 테스트할 파일 바로 옆에 `_test.go` 로 둬요.

```
slug/
├─ go.mod         // go mod init example.com/slug 로 만들어요
├─ slug.go        // 테스트할 함수
└─ slug_test.go   // 테스트
```

테스트할 함수는 이거예요. 글자와 숫자만 남기고, 나머지가 나오면 `-` 를 한 번만 넣어요. 끝에 남은 `-` 를 떼고 나서 길이를 봐요.

```go
// slug.go
// Package slug 는 글 제목을 URL에 넣을 조각으로 바꿔요.
package slug

import (
    "errors"
    "strings"
    "unicode"
    "unicode/utf8"
)

var (
    ErrEmpty   = errors.New("slug: 제목이 비어 있어요")
    ErrTooLong = errors.New("slug: 80자를 넘었어요")
)

// Slug 는 "Hello World" 를 "hello-world" 로 바꿔요.
// 글자와 숫자만 남기고, 나머지가 이어지면 "-" 하나로 줄여요.
func Slug(title string) (string, error) {
    var b strings.Builder
    dash := false
    for _, r := range strings.ToLower(title) {
        if unicode.IsLetter(r) || unicode.IsDigit(r) {
            b.WriteRune(r)
            dash = false
            continue
        }
        if !dash && b.Len() > 0 {
            b.WriteByte('-')
            dash = true
        }
    }
    s := strings.TrimSuffix(b.String(), "-")
    if s == "" {
        return "", ErrEmpty
    }
    if utf8.RuneCountInString(s) > 80 {
        return "", ErrTooLong
    }
    return s, nil
}
```

첫 테스트는 제일 단순하게 짜요. `"Hello World"` 하나만 넣고 결과를 `if` 로 비교해요. assert 함수가 없어서, 다르면 `t.Errorf` 로 직접 실패를 알려요.

```go
// slug_test.go
package slug

import "testing"

func TestSlugFirst(t *testing.T) {
    got, err := Slug("Hello World")
    if err != nil {
        t.Fatalf("Slug() err = %v", err)
    }
    if got != "hello-world" {
        t.Errorf(`Slug("Hello World") = %q, want "hello-world"`, got)
    }
}
```

`slug/` 폴더에서 `go test -v` 로 돌려요. `-v` 를 붙이면 테스트 이름마다 결과가 찍혀요.

```bash
$ go test -v .
=== RUN   TestSlugFirst
--- PASS: TestSlugFirst (0.00s)
PASS
ok  	example.com/slug	0.536s
```

테스트 하나가 통과했어요. 이제 이 테스트에 케이스를 하나씩 늘려 가면서, 왜 결국 표 모양이 되는지 볼게요.

## 03. `go test` 기본

방금 돌린 테스트로 규칙 두 개와 자주 쓰는 옵션을 짚고 넘어갈게요.

- **파일 이름은 `_test.go` 로 끝나요.** `slug.go` 옆에 `slug_test.go` 를 둬요. 같은 패키지라서 소문자로 시작하는 함수도 테스트할 수 있어요.
- **함수는 `func TestXxx(t *testing.T)` 모양이에요.** `Test` 로 시작하고 그 다음 글자는 대문자예요. 반환값은 없어요.

| 명령 | 하는 일 | PHPUnit으로 치면 |
|---|---|---|
| `go test ./...` | 하위 폴더까지 전부 실행 | `vendor/bin/phpunit` |
| `-v` | 테스트마다 PASS/FAIL과 `t.Log` 를 찍어요 | `--testdox` 비슷 |
| `-run 'TestSlug/경계값'` | 이름이 정규식에 맞는 테스트만 | `--filter` |
| `-count=1` | 캐시를 안 쓰고 진짜 다시 돌려요 | 없음 |
| `-race` | 데이터 레이스를 잡아요 | 없음 (PHP는 스레드가 없으니까요) |
| `-cover` | 커버리지 퍼센트 | `--coverage-text` |

Go는 코드가 안 바뀌었으면 이전 결과를 재사용하고 `(cached)` 를 붙여요. DB나 파일이 바뀌었는데 계속 통과하면 `-count=1` 로 다시 돌려요.

## 04. `if` 반복에서 표로

### 케이스를 늘리면 `if` 가 계속 늘어요

2장 표의 규칙 중에 한글 제목과 빈 문자열도 확인하고 싶어요. 2장 테스트에 그대로 이어 붙이면 이렇게 돼요.

```go
func TestSlugRepeat(t *testing.T) {
    got, err := Slug("Hello World")
    if err != nil || got != "hello-world" {
        t.Errorf(`Slug("Hello World") = %q, %v`, got, err)
    }
    got, err = Slug("Go 테스트 입문")
    if err != nil || got != "go-테스트-입문" {
        t.Errorf(`Slug("Go 테스트 입문") = %q, %v`, got, err)
    }
    _, err = Slug("")
    if !errors.Is(err, ErrEmpty) {
        t.Errorf(`Slug("") err = %v, want ErrEmpty`, err)
    }
}
```

돌리면 통과는 해요. 그런데 케이스 하나마다 "부르기 → 비교 → 메시지" 세 줄이 똑같이 반복되고, 입력값을 메시지에 또 적어야 해요. 케이스가 열 개가 되면 대부분이 복사한 코드예요.

### 바뀌는 것만 표로 빼요

반복되는 세 줄에서 케이스마다 다른 건 "넣는 값, 기대하는 값, 기대하는 에러" 뿐이에요. 그 세 칸을 struct로 만들고, 케이스를 그 struct의 슬라이스로 적어요. 비교하는 코드는 for문 안에 한 번만 써요. `slug_test.go` 의 테스트를 이렇게 바꿔요.

```go
func TestSlug(t *testing.T) {
    tests := []struct {
        name    string   // 케이스 이름. 실패하면 이 이름이 찍혀요
        in      string   // 넣는 값
        want    string   // 기대하는 값
        wantErr error    // 기대하는 에러. 안 적으면 nil
    }{
        {name: "영문 제목", in: "Hello World", want: "hello-world"},
        {name: "한글 섞임", in: "Go 테스트 입문", want: "go-테스트-입문"},
        {name: "빈 문자열", in: "", wantErr: ErrEmpty},
    }
    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            got, err := Slug(tc.in)
            if !errors.Is(err, tc.wantErr) {
                t.Fatalf("Slug(%q) err = %v, want %v", tc.in, err, tc.wantErr)
            }
            if got != tc.want {
                t.Errorf("Slug(%q) = %q, want %q", tc.in, got, tc.want)
            }
        })
    }
}
```

앞의 `TestSlugRepeat` 와 같은 세 케이스예요. 돌려 보면 케이스마다 줄이 하나씩 따로 찍혀요.

```bash
$ go test -v .
=== RUN   TestSlug
=== RUN   TestSlug/영문_제목
=== RUN   TestSlug/한글_섞임
=== RUN   TestSlug/빈_문자열
--- PASS: TestSlug (0.00s)
    --- PASS: TestSlug/영문_제목 (0.00s)       ← 케이스마다 서브테스트가 생겨요
    --- PASS: TestSlug/한글_섞임 (0.00s)
    --- PASS: TestSlug/빈_문자열 (0.00s)
PASS
ok  	example.com/slug	0.243s
```

- **`name` 필드가 제일 중요해요.** `t.Run(tc.name, ...)` 에 넘기면 케이스마다 `TestSlug/영문_제목` 같은 서브테스트가 생겨요. 이름의 공백은 `_` 로 바뀌어요.
- **필드 이름을 적어서 채워요.** `{"영문", "Hello", "hello", nil}` 처럼 순서로만 채우면 필드가 늘 때 다 고쳐야 하고, 읽을 때 뭐가 뭔지 몰라요. 안 적은 필드는 제로 값이라 `wantErr` 를 빼면 `nil` 이에요.
- **에러도 표의 한 칸이에요.** 성공 케이스는 `wantErr` 가 `nil` 이고, `errors.Is(nil, nil)` 은 `true` 라서 같은 비교 코드로 둘 다 확인돼요.

### `t.Errorf` 랑 `t.Fatalf` 는 언제 써요?

위 for문 안에서 에러 비교는 `Fatalf`, 값 비교는 `Errorf` 로 썼어요. 둘은 실패한 뒤에 계속 가느냐가 달라요.

| 함수 | 실패 후 | 쓰는 곳 |
|---|---|---|
| `t.Errorf` | 실패로 표시하고 **계속** 진행 | 값 비교. 틀린 곳을 한 번에 다 보고 싶을 때 |
| `t.Fatalf` | 실패로 표시하고 **그 서브테스트만** 바로 끝내요 | 에러가 났거나 nil이라서 다음 줄이 의미 없을 때 |

### 슬라이스 말고 map으로 짜도 돼요

표를 map으로 짜는 코드도 자주 보여요. 키가 케이스 이름이 돼서 `name` 필드가 없어져요.

```go
func TestSlugMap(t *testing.T) {
    tests := map[string]struct {
        in   string
        want string
    }{
        "정상/영문 제목":    {in: "Hello World", want: "hello-world"},
        "정상/한글 섞임":    {in: "Go 테스트 입문", want: "go-테스트-입문"},
        "경계값/특수문자 연속": {in: "a!!!b", want: "a-b"},
    }
    for name, tc := range tests {
        t.Run(name, func(t *testing.T) {
            got, _ := Slug(tc.in)
            if got != tc.want {
                t.Errorf("Slug(%q) = %q, want %q", tc.in, got, tc.want)
            }
        })
    }
}
```

같은 이름을 두 번 쓰면 컴파일 에러(`duplicate key`)가 나서 이름이 겹칠 걱정은 없어요. 대신 Go의 map은 꺼내는 순서가 정해져 있지 않아요. 같은 테스트를 세 번 돌려서 실행 순서만 뽑아 봤어요.

```bash
$ go test -count=1 -v -run TestSlugMap . | grep '=== RUN.*/'   # 세 번 반복
-- 1
=== RUN   TestSlugMap/정상/영문_제목
=== RUN   TestSlugMap/정상/한글_섞임
=== RUN   TestSlugMap/경계값/특수문자_연속
-- 2
=== RUN   TestSlugMap/경계값/특수문자_연속          ← 이번엔 이게 먼저 돌았어요
=== RUN   TestSlugMap/정상/영문_제목
=== RUN   TestSlugMap/정상/한글_섞임
-- 3
=== RUN   TestSlugMap/정상/영문_제목
=== RUN   TestSlugMap/정상/한글_섞임
=== RUN   TestSlugMap/경계값/특수문자_연속
```

세 번 중 한 번 순서가 바뀌었어요. 케이스끼리 독립적이면 문제없지만, 출력을 표 순서대로 읽고 싶으면 슬라이스를 써요. 이 글의 나머지 예제도 슬라이스로 짜요.

## 05. 정상/실패/경계값으로 나누기

4장 표에 2장 규칙의 나머지 케이스를 다 채워요. 저는 케이스를 늘 정상, 실패, 경계값 세 묶음으로 나눠요. 표 안에서 주석으로 묶고, 이름 앞에 묶음 이름과 `/` 를 붙여요.

```
// 정상
{name: "정상/영문 제목", in: "Hello World", want: "hello-world"},
{name: "정상/한글 섞임", in: "Go 테스트 입문", want: "go-테스트-입문"},
// 실패
{name: "실패/빈 문자열", in: "", wantErr: ErrEmpty},
{name: "실패/공백만", in: "   ", wantErr: ErrEmpty},
// 경계값
{name: "경계값/80자", in: strings.Repeat("a", 80), want: strings.Repeat("a", 80)},
{name: "경계값/81자", in: strings.Repeat("a", 81), wantErr: ErrTooLong},
{name: "경계값/특수문자 연속", in: "a!!!b", want: "a-b"},
```

경계값은 "딱 맞는 값"과 "하나 넘는 값"을 짝으로 넣어요. 80자 통과, 81자 실패처럼요. 하나만 넣으면 `>` 와 `>=` 를 헷갈린 버그를 못 잡아요.

### 묶음 이름으로 골라 돌리기

이름에 `/` 를 넣으면 한 단계 더 들어간 서브테스트처럼 다뤄져요. 그래서 경계값 묶음만 골라 돌릴 수 있어요.

```bash
$ go test -v -run 'TestSlug/경계값' .
=== RUN   TestSlug
=== RUN   TestSlug/경계값/80자
=== RUN   TestSlug/경계값/81자
=== RUN   TestSlug/경계값/특수문자_연속
--- PASS: TestSlug (0.00s)
    --- PASS: TestSlug/경계값/80자 (0.00s)
    --- PASS: TestSlug/경계값/81자 (0.00s)
    --- PASS: TestSlug/경계값/특수문자_연속 (0.00s)
PASS
```

여기서 함정이 하나 있어요. 81자 케이스 하나만 돌리려고 이름 끝부분만 적어 봤어요.

```bash
$ go test -v -run 'TestSlug/81자' .
=== RUN   TestSlug
--- PASS: TestSlug (0.00s)                ← PASS인데 서브테스트가 하나도 없어요
testing: warning: no tests to run
PASS
ok  	example.com/slug	0.187s [no tests to run]

$ go test -v -run 'TestSlug//81자' .
=== RUN   TestSlug
=== RUN   TestSlug/경계값/81자
--- PASS: TestSlug (0.00s)
    --- PASS: TestSlug/경계값/81자 (0.00s)
```

첫 번째는 아무 케이스도 안 돌렸는데 `PASS` 가 찍혀요. `-run` 은 `/` 로 나눈 단계마다 따로 맞춰 보는데, 두 번째 단계 이름은 `경계값` 이라서 `81자` 와 안 맞거든요. `-run 'TestSlug/경계값/81자'` 처럼 단계를 다 적거나, 두 번째 단계를 비워서 `-run 'TestSlug//81자'` 로 써요.

### 일부러 하나 틀리면 이렇게 나와요

실패 출력이 어떻게 생겼는지 보려고, 마지막 케이스의 기대값을 `"a-b"` 에서 `"a--b"` 로 일부러 틀리게 바꾸고 돌렸어요.

```bash
$ go test -v .
=== RUN   TestSlug
=== RUN   TestSlug/정상/영문_제목
=== RUN   TestSlug/정상/한글_섞임
=== RUN   TestSlug/실패/빈_문자열
=== RUN   TestSlug/실패/공백만
=== RUN   TestSlug/경계값/80자
=== RUN   TestSlug/경계값/81자
=== RUN   TestSlug/경계값/특수문자_연속
    slug_test.go:34: Slug("a!!!b") = "a-b", want "a--b"     ← 입력, 실제값, 기대값
--- FAIL: TestSlug (0.00s)
    --- PASS: TestSlug/정상/영문_제목 (0.00s)
    --- PASS: TestSlug/정상/한글_섞임 (0.00s)
    --- PASS: TestSlug/실패/빈_문자열 (0.00s)
    --- PASS: TestSlug/실패/공백만 (0.00s)
    --- PASS: TestSlug/경계값/80자 (0.00s)
    --- PASS: TestSlug/경계값/81자 (0.00s)
    --- FAIL: TestSlug/경계값/특수문자_연속 (0.00s)        ← 어느 케이스인지 이름으로 보여요
FAIL
```

어느 케이스가 깨졌는지 이름으로 바로 보이고, 나머지 케이스는 계속 돌아요. 메시지는 `함수(입력) = 실제값, want 기대값` 모양으로 쓰는 게 관례예요. 기대값을 되돌리면 일곱 개 다 통과하고, `-race -cover` 로 돌리면 `coverage: 100.0% of statements` 가 나와요.

<details>
<summary>완성한 slug_test.go 전체 보기</summary>

```go
package slug

import (
    "errors"
    "strings"
    "testing"
)

func TestSlug(t *testing.T) {
    tests := []struct {
        name    string
        in      string
        want    string
        wantErr error
    }{
        // 정상
        {name: "정상/영문 제목", in: "Hello World", want: "hello-world"},
        {name: "정상/한글 섞임", in: "Go 테스트 입문", want: "go-테스트-입문"},
        // 실패
        {name: "실패/빈 문자열", in: "", wantErr: ErrEmpty},
        {name: "실패/공백만", in: "   ", wantErr: ErrEmpty},
        // 경계값
        {name: "경계값/80자", in: strings.Repeat("a", 80), want: strings.Repeat("a", 80)},
        {name: "경계값/81자", in: strings.Repeat("a", 81), wantErr: ErrTooLong},
        {name: "경계값/특수문자 연속", in: "a!!!b", want: "a-b"},
    }
    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            got, err := Slug(tc.in)
            if !errors.Is(err, tc.wantErr) {
                t.Fatalf("Slug(%q) err = %v, want %v", tc.in, err, tc.wantErr)
            }
            if got != tc.want {
                t.Errorf("Slug(%q) = %q, want %q", tc.in, got, tc.want)
            }
        })
    }
}
```

`slug.go` 는 2장 코드 그대로예요. 두 파일을 한 폴더에 두고 `go mod init example.com/slug` 다음 `go test -v .` 로 돌려요.

</details>

## 06. 병렬 실행, `t.Helper`, `t.Cleanup`

### `t.Parallel()` 과 루프 변수

**상황:** 케이스가 많아지면 동시에 돌려서 시간을 줄이고 싶어져요. 서브테스트 첫 줄에 `t.Parallel()` 을 넣으면 케이스들이 동시에 돌아요. 이때 for문이 먼저 끝까지 돌고, 서브테스트는 그 뒤에 한꺼번에 실행돼요.

**해 본 것:** Slug 표에서 세 케이스만 남기고 `t.Parallel()` 을 붙였어요. 각 서브테스트가 실제로 어떤 값을 받았는지 보려고 `t.Logf` 로 `tc.in` 을 찍어요.

```go
tests := []struct {
    name string
    in   string
    want string
}{
    {name: "정상/영문 제목", in: "Hello World", want: "hello-world"},
    {name: "정상/한글 섞임", in: "Go 테스트 입문", want: "go-테스트-입문"},
    {name: "경계값/특수문자 연속", in: "a!!!b", want: "a-b"},
}
for _, tc := range tests {
    t.Run(tc.name, func(t *testing.T) {
        t.Parallel()
        t.Logf("tc.in = %q", tc.in)
        got, _ := Slug(tc.in)
        if got != tc.want {
            t.Errorf("Slug(%q) = %q, want %q", tc.in, got, tc.want)
        }
    })
}
```

**결과:** 같은 Go 1.26으로 `go.mod` 의 `go` 줄만 바꿔서 두 번 돌렸어요.

```
// go.mod 가 go 1.21 일 때
parallel_test.go:18: tc.in = "a!!!b"
parallel_test.go:18: tc.in = "a!!!b"
parallel_test.go:18: tc.in = "a!!!b"       ← 세 케이스가 모두 마지막 값을 봐요
ok  	example.com/slug	0.278s              ← 그런데 통과해요

// go.mod 를 go 1.22 로 바꾸면
parallel_test.go:18: tc.in = "Hello World"
parallel_test.go:18: tc.in = "a!!!b"
parallel_test.go:18: tc.in = "Go 테스트 입문"
ok  	example.com/slug	0.245s
```

1.21에서는 세 서브테스트가 전부 `"a!!!b"` 만 확인했는데도 `ok` 가 나왔어요. 마지막 케이스가 맞으니 다 통과한 것처럼 보이는 거예요. 실패하지 않으니 알아채기도 어려워요.

**왜:** Go 1.21까지는 for문 변수 `tc` 하나를 모든 반복이 같이 썼어요. 서브테스트가 실행될 때쯤엔 for문이 끝나서 `tc` 에 마지막 값이 들어 있어요. 그래서 예전 글에는 `tc := tc` 가 꼭 있어요. Go 1.22부터는 반복마다 변수가 새로 생겨서 이 줄이 필요 없어요. 기준은 설치된 Go가 아니라 **`go.mod` 의 `go` 줄**이에요.

### `t.Helper()` — 실패 줄 번호를 호출한 쪽으로

**상황:** 비교 코드가 여러 테스트에 반복되면 `assertSlug(t, 넣는 값, 기대값)` 같은 도우미 함수로 빼고 싶어져요. 그런데 이렇게 빼면 실패했을 때 찍히는 줄 번호가 문제가 돼요.

**해 본 것:** 도우미 함수를 만들고, 두 번째 호출에 일부러 틀린 기대값을 넣었어요.

```go
func assertSlug(t *testing.T, in, want string) {
    t.Helper()                          // 이 줄을 넣고 한 번, 주석 처리하고 한 번 돌려요
    got, err := Slug(in)
    if err != nil {
        t.Fatalf("Slug(%q) err = %v", in, err)
    }
    if got != want {
        t.Errorf("Slug(%q) = %q, want %q", in, got, want)   // 12번째 줄
    }
}

func TestSlugHelper(t *testing.T) {
    assertSlug(t, "Hello World", "hello-world")
    assertSlug(t, "a!!!b", "a--b") // 일부러 틀린 기대값  ← 18번째 줄
}
```

**결과:**

```
// t.Helper() 없음 — 도우미 함수 안의 줄이 찍혀요
helper_test.go:12: Slug("a!!!b") = "a-b", want "a--b"

// t.Helper() 있음 — 테스트에서 부른 줄이 찍혀요
helper_test.go:18: Slug("a!!!b") = "a-b", want "a--b"
```

**왜:** `t.Helper()` 는 "이 함수는 도우미니까 실패 위치를 셀 때 건너뛰어"라는 표시예요. 없으면 도우미를 열 번 불러도 실패 줄이 다 12번으로 나와서 어느 호출이 깨졌는지 몰라요. 도우미 함수 첫 줄에는 늘 넣어 둬요.

### `t.Cleanup()` — 테스트 끝나면 정리

Slug는 파일을 안 쓰지만, 설정 파일을 읽는 함수처럼 임시 폴더가 필요한 테스트도 많아요. 준비하는 코드 바로 아래에 정리할 일을 등록해 둬요.

```go
dir, err := os.MkdirTemp("", "cfg")
if err != nil {
    t.Fatal(err)
}
t.Cleanup(func() { os.RemoveAll(dir) })   // 테스트가 끝나면 실행돼요
```

PHPUnit의 `tearDown()` 역할인데, 준비하는 함수 안에서 정리까지 같이 등록할 수 있어요. `defer` 는 그 함수가 끝날 때 돌지만 `t.Cleanup` 은 **테스트가** 끝날 때 돌아요. 그래서 도우미 함수에서는 `defer` 말고 `t.Cleanup` 을 써요. 임시 폴더만 필요하면 `t.TempDir()` 이 만들고 지우는 것까지 다 해 줘요.

## 07. struct 비교: `reflect.DeepEqual`, go-cmp, testify

Slug는 문자열 하나를 돌려줘서 `!=` 로 비교하면 됐어요. 결과가 struct면 얘기가 달라져요. 장바구니 금액을 계산하는 함수를 하나 더 만들어서 볼게요. 쿠폰은 할인 퍼센트예요.

```go
// price.go
package price

// Order 는 장바구니예요. Items 는 상품 가격 목록이에요.
type Order struct {
    Items  []int
    Coupon int // 할인 퍼센트 (10 = 10%)
}

// Price 는 계산 결과예요.
type Price struct {
    Subtotal int
    Discount int
    Total    int
}

// Calc 는 상품 가격을 더하고 쿠폰 할인을 빼요.
func Calc(o Order) Price {
    sum := 0
    for _, v := range o.Items {
        sum += v
    }
    d := sum * o.Coupon / 100
    return Price{Subtotal: sum, Discount: d, Total: sum - d}
}
```

`Price` 는 int 필드만 있어서 `==` 로 비교돼요. 그런데 `Order` 처럼 슬라이스가 들어 있는 struct는 `==` 를 쓰면 컴파일부터 안 돼요.

```
if (Order{}) == (Order{}) { ... }
// ./eq_test.go:6:5: invalid operation: (Order{}) == (Order{}) (struct containing []int cannot be compared)
```

그래서 struct는 보통 아래 셋 중 하나로 비교해요.

| 방법 | 장점 | 아쉬운 점 |
|---|---|---|
| `reflect.DeepEqual` | 표준 라이브러리 | 어디가 다른지 안 알려 줘요 |
| `cmp.Diff` (`github.com/google/go-cmp`) | 다른 필드만 `-`/`+` 로 보여 줘요 | 외부 모듈. 테스트 전용이라 부담은 적어요 |
| `assert.Equal` (`github.com/stretchr/testify`) | PHPUnit `assertEquals` 랑 제일 비슷해요 | 팀마다 쓰는지 안 쓰는지 갈려요 |

앞 두 방법의 실패 메시지를 비교해 보려고, 10% 쿠폰 케이스의 `Total` 기대값을 900이 아니라 1000으로 일부러 틀리게 넣었어요.

```go
func TestCalc(t *testing.T) {
    tests := []struct {
        name string
        in   Order
        want Price
    }{
        {name: "정상/쿠폰 없음", in: Order{Items: []int{1000, 2000}}, want: Price{Subtotal: 3000, Total: 3000}},
        {name: "정상/10% 쿠폰", in: Order{Items: []int{1000}, Coupon: 10}, want: Price{Subtotal: 1000, Discount: 100, Total: 1000}}, // Total 일부러 틀림
        {name: "경계값/빈 주문", in: Order{}, want: Price{}},
    }
    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            got := Calc(tc.in)
            if !reflect.DeepEqual(got, tc.want) {
                t.Errorf("DeepEqual: got %+v, want %+v", got, tc.want)
            }
            if diff := cmp.Diff(tc.want, got); diff != "" {
                t.Errorf("Calc() mismatch (-want +got):\n%s", diff)
            }
        })
    }
}
```

돌리면 같은 실패가 두 방식으로 찍혀요.

```
=== RUN   TestCalc/정상/10%_쿠폰
    price_test.go:24: DeepEqual: got {Subtotal:1000 Discount:100 Total:900}, want {Subtotal:1000 Discount:100 Total:1000}
    price_test.go:27: Calc() mismatch (-want +got):
          price.Price{
          	Subtotal: 1000,
          	Discount: 100,
        - 	Total:    1000,       ← 기대값
        + 	Total:    900,        ← 실제값
          }
```

`DeepEqual` 쪽은 두 값을 통째로 찍어서 다른 곳을 눈으로 찾아야 해요. 필드가 많아질수록 `cmp.Diff` 가 편해요. 인자 순서는 `cmp.Diff(want, got)` 로 맞추고 메시지에 `(-want +got)` 을 적는 게 관례예요.

nil 슬라이스와 빈 슬라이스는 `DeepEqual` 도 `cmp.Equal` 도 다르다고 봐요. `var a []int` 와 `[]int{}` 를 넣어 보니 둘 다 `false` 였어요. 03편처럼 JSON에서 `null` 과 `[]` 로 갈리니까 잡아 주는 게 맞을 때가 많고, 상관없을 때만 `cmpopts.EquateEmpty()` 를 붙여요.

## 08. HTTP 핸들러 테스트와 golden 파일

API 핸들러도 같은 표로 테스트해요. 이번엔 이메일 형식을 검사하는 작은 핸들러를 예로 들게요. `GET /email/validate?email=...` 를 받아서, 파라미터가 없으면 400, 있으면 형식이 맞는지를 JSON으로 돌려줘요.

```go
// email.go
package web

// ValidateEmail 은 GET /email/validate?email=... 을 받아서
// 형식이 맞는지 JSON으로 알려 줘요.
func ValidateEmail(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    email := r.URL.Query().Get("email")
    if email == "" {
        w.WriteHeader(http.StatusBadRequest)
        json.NewEncoder(w).Encode(map[string]string{"error": "email is required"})
        return
    }
    local, domain, ok := strings.Cut(email, "@")
    valid := ok && local != "" && strings.Contains(domain, ".")
    json.NewEncoder(w).Encode(map[string]bool{"valid": valid})
}
```

서버를 띄우지 않고 이 함수를 바로 부를 수 있어요. `net/http/httptest` 의 `NewRequest` 로 가짜 요청을 만들고, `NewRecorder` 가 응답을 받아 둬요. 표의 칸은 "쿼리 문자열, 기대하는 상태 코드, 기대하는 본문"이에요.

```go
func TestValidateEmail(t *testing.T) {
    tests := []struct {
        name     string
        query    string
        wantCode int
        wantBody string
    }{
        {"정상/형식 맞음", "?email=a@b.com", http.StatusOK, `{"valid":true}`},
        {"실패/파라미터 없음", "", http.StatusBadRequest, `{"error":"email is required"}`},
        {"경계값/로컬 파트 빈 값", "?email=@b.com", http.StatusOK, `{"valid":false}`},
    }
    for _, tc := range tests {
        t.Run(tc.name, func(t *testing.T) {
            req := httptest.NewRequest(http.MethodGet, "/email/validate"+tc.query, nil)
            rec := httptest.NewRecorder()

            ValidateEmail(rec, req)

            if rec.Code != tc.wantCode {
                t.Errorf("status = %d, want %d", rec.Code, tc.wantCode)
            }
            if got := strings.TrimSpace(rec.Body.String()); got != tc.wantBody {
                t.Errorf("body = %s, want %s", got, tc.wantBody)
            }
        })
    }
}
```

세 케이스 다 통과해요. 본문 비교에 `strings.TrimSpace` 를 넣은 이유가 있어요. `json.NewEncoder` 는 JSON 끝에 줄바꿈을 붙여요. `TrimSpace` 를 빼고 돌려 보면 이렇게 실패해요.

```
--- FAIL: TestValidateEmail (0.00s)
    --- FAIL: TestValidateEmail/정상/형식_맞음 (0.00s)
        email_test.go:37: body = {"valid":true}
            , want {"valid":true}                 ← 줄바꿈 하나 때문에 달라요
```

눈으로는 똑같아 보이는데 실패해서 한참 헤매기 쉬워요. gin 핸들러도 `gin.CreateTestContext(rec)` 나 라우터의 `ServeHTTP(rec, req)` 로 같은 방식으로 테스트해요.

### golden 파일

응답이 길면 기대값을 표에 다 넣기 힘들어요. 그럴 땐 기대값을 `testdata/xxx.golden` 파일로 두고 비교해요. 위 핸들러의 "파라미터 없음" 응답으로 해 볼게요. `-update` 플래그를 주면 지금 응답으로 파일을 새로 쓰고, 없으면 파일과 비교만 해요.

```go
var update = flag.Bool("update", false, "golden 파일을 새로 써요")

func TestGolden(t *testing.T) {
    req := httptest.NewRequest(http.MethodGet, "/email/validate", nil)
    rec := httptest.NewRecorder()
    ValidateEmail(rec, req)

    golden := filepath.Join("testdata", "missing_email.golden")
    if *update {
        os.MkdirAll("testdata", 0o755)
        os.WriteFile(golden, rec.Body.Bytes(), 0o644)
    }
    want, err := os.ReadFile(golden)
    if err != nil {
        t.Fatal(err)
    }
    if diff := cmp.Diff(string(want), rec.Body.String()); diff != "" {
        t.Errorf("golden mismatch (-want +got):\n%s", diff)
    }
}
```

세 번 이어서 돌려 봤어요.

```bash
$ go test -run TestGolden .            # 1. 아직 파일이 없어요
--- FAIL: TestGolden (0.00s)
    email_test.go:57: open testdata/missing_email.golden: no such file or directory

$ go test -run TestGolden . -update    # 2. 파일을 만들어요
ok  	example.com/web	0.245s

$ go test -run TestGolden .            # 3. 이제 파일과 비교해서 통과해요
ok  	example.com/web	0.239s

$ cat testdata/missing_email.golden
{"error":"email is required"}
```

`-update` 는 지금 응답이 맞다고 믿고 덮어써요. 그래서 새로 쓴 파일은 **꼭 diff를 눈으로 보고** 커밋해요.

## 09. PHPUnit, JUnit이랑 비교하면

같은 Slug 테스트를 PHPUnit으로 짜면 이런 모양이에요. 입력과 기대값이 provider 메서드로 떨어져 나가요.

```
// PHPUnit (PHP 7.4) — 이 블록은 돌려 보지 않은 예시예요
/** @dataProvider slugProvider */
public function testSlug(string $in, string $want): void
{
    $this->assertSame($want, Slug::make($in));
}

public function slugProvider(): array
{
    return [
        '정상/영문 제목' => ['Hello World', 'hello-world'],
        '경계값/특수문자 연속' => ['a!!!b', 'a-b'],
    ];
}
```

| PHPUnit / JUnit | Go | 메모 |
|---|---|---|
| `@dataProvider`, `@ParameterizedTest` | struct 슬라이스 + for문 | 어노테이션이 없어요 |
| provider 배열의 키, `name = "{0}"` | `t.Run(tc.name, ...)` | 실패 출력에 그대로 나와요 |
| `assertSame`, `assertEquals` | `if got != want { t.Errorf }` | testify를 쓰면 `assert.Equal` |
| `expectException`, `assertThrows` | `errors.Is(err, tc.wantErr)` | 에러도 표의 한 칸이에요 |
| `setUp` / `tearDown`, `@BeforeEach` | 테스트 안에서 직접, `t.Cleanup` | 전체 준비는 `TestMain` |
| `--filter` | `-run` | `/` 단계마다 맞춰요 |
| 테스트 클래스 하나 | `_test.go` 파일 하나 | 같은 패키지라 소문자 함수도 테스트돼요 |

제일 큰 차이는 **expected 값을 표 안에 같이 둔다**는 점이에요. PHPUnit은 provider와 테스트 메서드가 떨어져 있어서 "이 배열의 두 번째 칸이 뭐였지?" 하고 위아래로 오가잖아요. Go는 필드 이름이 붙은 한 줄에 입력과 기대값이 다 있어요.

## 10. 조심할 것

- **map 표는 실행 순서가 매번 달라요.** 4장에서 본 것처럼 같은 테스트도 돌릴 때마다 순서가 바뀌어요. 앞 케이스가 만든 데이터를 뒤 케이스가 쓰면 가끔만 깨지는 테스트가 돼요. 케이스는 서로 독립적으로 만들어요.
- **고루틴 안에서 `t.Fatal` 을 부르면 테스트가 안 멈춰요.** 테스트 안에서 고루틴을 띄우고, 그 안에서 `t.Fatal` 을 불러 봤어요. `func TestFatalInGoroutine(t *testing.T) {
 var wg sync.WaitGroup
 wg.Add(1)
 go func() {
 defer wg.Done()
 t.Fatal("고루틴에서 Fatal")
 }()
 wg.Wait()
 t.Log("테스트 함수는 계속 돌아요")
}

// 결과
fatal_test.go:13: 고루틴에서 Fatal
fatal_test.go:16: 테스트 함수는 계속 돌아요 ← Fatal 다음에도 실행됐어요` `Fatal` 은 자기를 부른 고루틴만 끝내요. 테스트 함수는 계속 돌아요. `go vet` 은 `call to (*testing.T).Fatal from a non-test goroutine` 으로 잡아 줘요. 고루틴에서는 `t.Error` 를 쓰거나, 결과를 채널로 받아서 테스트 고루틴에서 판단해요.
- **병렬 케이스끼리 같은 값을 쓰면 레이스가 나요.** 패키지 전역 변수를 `t.Parallel()` 케이스 네 개에서 같이 올려 봤어요. `var counter int

func TestShared(t *testing.T) {
 for _, name := range []string{"a", "b", "c", "d"} {
 t.Run(name, func(t *testing.T) {
 t.Parallel()
 counter++
 })
 }
}

$ go test -run TestShared . ← -race 없이
ok 	example.com/pit	0.205s

$ go test -race -run TestShared .
WARNING: DATA RACE
 testing.go:1712: race detected during execution of test
FAIL` `-race` 없이는 그냥 통과해요. 공유하는 값은 케이스마다 새로 만들고, CI에서는 `-race` 를 켜 둬요.
- **이름 없이 짜면 어느 케이스가 깨졌는지 몰라요.** `t.Run` 없이 for문 안에서 바로 `t.Errorf` 를 부르고, 세 케이스 중 두 개를 일부러 틀리게 넣었어요. `tests := []struct{ a, b, want int }{
 {2, 2, 5}, // 일부러 틀림
 {1, 1, 2},
 {5, 5, 11}, // 일부러 틀림
}
for _, tc := range tests {
 if got := Add(tc.a, tc.b); got != tc.want {
 t.Errorf("got %d, want %d", got, tc.want)
 }
}

--- FAIL: TestAdd (0.00s)
 noname_test.go:15: got 4, want 5
 noname_test.go:15: got 10, want 11 ← 줄 번호가 다 같아요` 줄 번호가 다 같아서 표의 몇 번째 줄인지 직접 찾아야 해요. `t.Run` 에 이름을 붙이고, 이름에는 "무엇을 확인하는지"를 적어요.

## 11. 스스로 확인해 보기

#### 1. 표에 `{name: "경계값/81자", ...}` 케이스가 있어요. `go test -run 'TestSlug/81자'` 로 이 케이스만 돌리려고 했는데 `no tests to run` 이 나왔어요. 왜일까?

<details>
<summary>답 보기</summary>

이름의 `/` 때문에 이 케이스는 `TestSlug` → `경계값` → `81자` 세 단계가 됐어요. `-run` 은 단계마다 따로 맞춰 보는데, 두 번째 단계 `경계값` 이 `81자` 에 안 맞아서 아무것도 안 골라요. `-run 'TestSlug/경계값/81자'` 나 `-run 'TestSlug//81자'` 로 돌려요.

</details>

#### 2. 모든 서브테스트에 `t.Parallel()` 을 붙이고 로컬에서 `go test ./...` 로 돌리면 잘 통과해요. 그런데 CI(`go test -race ./...`)에서만 가끔 실패해요. 뭘 먼저 의심할까?

<details>
<summary>답 보기</summary>

케이스끼리 같이 쓰는 값이에요. 패키지 전역 변수, 표 바깥에서 한 번 만든 mock이나 map, 같은 DB 행 같은 거요. `-race` 가 없으면 레이스가 있어도 통과할 수 있어요. 로컬에서도 `-race -count=1` 로 돌려서 재현하고, 공유하는 값은 서브테스트 안에서 새로 만들어요.

</details>

## 12. 참고한 글

- [Go 테스트 코드 작성 및 실행](https://devocean.sk.com/experts/techBoardDetail.do?ID=163605) — SK DEVOCEAN. `_test.go` 규칙, 테이블 주도 테스트로 중복 줄이기
- [TDD로 배우는 Golang](https://velog.io/@tmdgh0221/TDD%EB%A1%9C-%EB%B0%B0%EC%9A%B0%EB%8A%94-Golang) — velog. `t.Run`, `t.Helper`, 익명 struct 슬라이스, `reflect.DeepEqual`
- [GO Test code - 1일차 테스트 코드 작성, coverage 확인 방법](https://velog.io/@chappi/GO-Test-code-1%EC%9D%BC%EC%B0%A8-golang%EC%97%90%EC%84%9C-%ED%85%8C%EC%8A%A4%ED%8A%B8-%EC%BD%94%EB%93%9C-%EC%9E%91%EC%84%B1-coverage-%ED%99%95%EC%9D%B8-%EB%B0%A9%EB%B2%95) — velog. `-cover`, `-coverprofile`, `go tool cover -html`
- [Golang 프로젝트에 TDD 도입하기](https://golangkorea.github.io/post/tdd-with-golang/) — Golang Korea. `httptest` 로 핸들러 테스트하기
- [Go 테스트 자동화: Unit 테스트부터 Integration 테스트까지](https://devocean.sk.com/blog/techBoardDetail.do?ID=167575&boardType=techBlog) — SK DEVOCEAN. testify assert/mock, 테스트 옵션
- [\[Golang\] go 1.22](https://velog.io/@excellent/Golang-go-1.22) — velog. 1.22에서 for문 변수가 반복마다 새로 생기게 바뀐 내용
