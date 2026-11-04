---
title: "07. Go에서는 테스트를 왜 표로 짤까? (table-driven test)"
date: 2026-11-04
tags: ["Go"]
---

# 07. Go에서는 테스트를 왜 표로 짤까? (table-driven test)

**Go 학습 · 07**

Go 테스트 코드를 열어 보면 거의 다 `tests := []struct{...}` 로 시작해요. PHPUnit의 `@dataProvider` 나 JUnit의 `@ParameterizedTest` 를 써 봤다면 금방 익숙해지는데, Go에는 어노테이션이 없어서 모양이 꽤 달라 보여요. 이 글에서는 `go test` 기본부터 표로 짜는 법, 정상/실패/경계값으로 나누는 법, 병렬 실행할 때 걸리는 곳까지 정리해요. 예제는 전부 Go 1.26에서 직접 돌려 본 결과예요.

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

## 02. `go test` 기본

- **파일 이름은 `_test.go` 로 끝나요.** `slug.go` 옆에 `slug_test.go` 를 둬요. `tests/` 폴더를 따로 두지 않아요.
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

## 03. 표로 짜기

제목을 URL 조각으로 바꾸는 `Slug(title) (string, error)` 함수를 테스트해 볼게요. 빈 문자열이면 `ErrEmpty`, 80자를 넘으면 `ErrTooLong` 을 돌려줘요.

```go
func TestSlug(t *testing.T) {
    tests := []struct {
        name    string
        in      string
        want    string
        wantErr error
    }{
        {name: "정상/영문 제목", in: "Hello World", want: "hello-world"},
        {name: "실패/빈 문자열", in: "", wantErr: ErrEmpty},
        // ... 4장에서 정상/실패/경계값을 다 채워요
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

- **`name` 필드가 제일 중요해요.** `t.Run(tc.name, ...)` 에 넘기면 케이스마다 `TestSlug/정상/영문_제목` 같은 서브테스트가 생겨요. 이름의 공백은 `_` 로 바뀌어요.
- **필드 이름을 적어서 채워요.** `{"정상", "Hello", "hello", nil}` 처럼 순서로만 채우면 필드가 늘 때 다 고쳐야 하고, 읽을 때 뭐가 뭔지 몰라요. 안 적은 필드는 제로 값이라 `wantErr` 를 빼면 `nil` 이에요.

### 일부러 하나 틀리면 이렇게 나와요

```
=== RUN   TestAdd
=== RUN   TestAdd/정상/양수
=== RUN   TestAdd/경계값/0_더하기
=== RUN   TestAdd/실패_예시/일부러_틀린_기대값
    price_test.go:20: Add(2, 2) = 4, want 5
--- FAIL: TestAdd (0.00s)
    --- PASS: TestAdd/정상/양수 (0.00s)
    --- PASS: TestAdd/경계값/0_더하기 (0.00s)
    --- FAIL: TestAdd/실패_예시/일부러_틀린_기대값 (0.00s)
FAIL
```

어느 케이스가 깨졌는지 이름으로 바로 보이고, 나머지 케이스는 계속 돌아요. 메시지는 `함수(입력) = 실제값, want 기대값` 모양이 관례예요.

### `t.Errorf` 랑 `t.Fatalf` 는 언제 써요?

| 함수 | 실패 후 | 쓰는 곳 |
|---|---|---|
| `t.Errorf` | 실패로 표시하고 **계속** 진행 | 값 비교. 틀린 곳을 한 번에 다 보고 싶을 때 |
| `t.Fatalf` | 실패로 표시하고 **그 서브테스트만** 바로 끝내요 | 에러가 났거나 nil이라서 다음 줄이 의미 없을 때 |

### 슬라이스 말고 map으로 짜도 돼요

```go
tests := map[string]struct {
    in   Order
    want Price
}{
    "정상/쿠폰 없음": {in: Order{Items: []int{1000, 2000}}, want: Price{Subtotal: 3000, Total: 3000}},
    "경계값/빈 주문": {in: Order{}, want: Price{}},
}
for name, tc := range tests {
    t.Run(name, func(t *testing.T) { /* ... */ })
}
```

키가 이름이라 `name` 필드가 필요 없고, 같은 이름을 두 번 쓰면 컴파일 에러(`duplicate key`)가 나요. 대신 **실행 순서가 매번 바뀌어요.** 세 번 돌려 보니 세 번 다 순서가 달랐어요. 출력을 위에서부터 읽고 싶으면 슬라이스를 써요.

## 04. 정상/실패/경계값으로 나누기

저는 테스트 케이스를 늘 정상, 실패, 경계값 세 묶음으로 나눠요. 표 안에서 주석으로 묶고, 이름 앞에 묶음 이름을 붙여요.

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

이름에 `/` 를 넣으면 한 단계 더 들어간 서브테스트처럼 다뤄져요. 그래서 묶음 단위로 골라 돌릴 수 있어요.

```bash
$ go test -v -run 'TestSlug/경계값' .
--- PASS: TestSlug (0.00s)
    --- PASS: TestSlug/경계값/80자 (0.00s)
    --- PASS: TestSlug/경계값/특수문자_연속 (0.00s)
    --- PASS: TestSlug/경계값/81자 (0.00s)
```

대신 함정이 하나 있어요. `-run 'TestSlug/81자'` 는 **아무것도 안 돌려요** (`no tests to run`). `-run` 은 `/` 로 나눈 단계마다 따로 맞춰 보는데, 두 번째 단계 이름은 `경계값` 이거든요. `-run 'TestSlug/경계값/81자'` 나 `-run 'TestSlug//81자'` 처럼 단계를 맞춰 써요.

경계값은 "딱 맞는 값"과 "하나 넘는 값"을 짝으로 넣어요. 80자 통과, 81자 실패처럼요. 하나만 넣으면 `>` 와 `>=` 를 헷갈린 버그를 못 잡아요.

## 05. 병렬 실행, `t.Helper`, `t.Cleanup`

### `t.Parallel()` 과 루프 변수

서브테스트 첫 줄에 `t.Parallel()` 을 넣으면 케이스들이 동시에 돌아요. 이때 for문이 먼저 끝나고 서브테스트가 나중에 실행돼요. 옛날 Go에서는 여기서 유명한 버그가 났어요.

```go
for _, tc := range tests {
    t.Run(tc.name, func(t *testing.T) {
        t.Parallel()
        t.Logf("tc.in = %d", tc.in)
    })
}

// go.mod 가 go 1.21 일 때 — 세 케이스가 모두 마지막 값을 봐요
loop_test.go:13: tc.in = 3
loop_test.go:13: tc.in = 3
loop_test.go:13: tc.in = 3

// go.mod 를 go 1.22 로 바꾸면
loop_test.go:13: tc.in = 1
loop_test.go:13: tc.in = 2
loop_test.go:13: tc.in = 3
```

Go 1.21까지는 for문 변수 하나를 모든 반복이 같이 썼어요. 그래서 예전 글에는 `tc := tc` 가 꼭 있어요. Go 1.22부터는 반복마다 변수가 새로 생겨서 이 줄이 필요 없어요. 기준은 설치된 Go가 아니라 **`go.mod` 의 `go` 줄**이에요. 위 결과도 같은 Go 1.26에서 `go.mod` 만 바꿔서 돌렸어요.

### `t.Helper()` — 실패 줄 번호를 호출한 쪽으로

비교 코드를 `assertEqual(t, got, want)` 같은 함수로 빼면 실패 위치가 그 함수 안으로 찍혀요. 직접 돌려 보니 `t.Helper()` 가 없을 땐 `helper_test.go:26` (도우미 함수 안), 있을 땐 `helper_test.go:35` (테스트에서 부른 줄)로 나왔어요. 도우미 함수 첫 줄에는 늘 넣어 둬요.

### `t.Cleanup()` — 테스트 끝나면 정리

```go
dir, err := os.MkdirTemp("", "cfg")
if err != nil {
    t.Fatal(err)
}
t.Cleanup(func() { os.RemoveAll(dir) })   // 테스트가 끝나면 실행돼요
```

PHPUnit의 `tearDown()` 역할인데, 준비하는 함수 안에서 정리까지 같이 등록할 수 있어요. `defer` 는 그 함수가 끝날 때 돌지만 `t.Cleanup` 은 **테스트가** 끝날 때 돌아요. 그래서 도우미 함수에서는 `defer` 말고 `t.Cleanup` 을 써요. 임시 폴더만 필요하면 `t.TempDir()` 이 만들고 지우는 것까지 다 해 줘요.

## 06. struct 비교: `reflect.DeepEqual`, go-cmp, testify

struct에 슬라이스나 map이 들어 있으면 `==` 가 컴파일이 안 돼요.

| 방법 | 장점 | 아쉬운 점 |
|---|---|---|
| `reflect.DeepEqual` | 표준 라이브러리 | 어디가 다른지 안 알려 줘요 |
| `cmp.Diff` (`github.com/google/go-cmp`) | 다른 필드만 `-`/`+` 로 보여 줘요 | 외부 모듈. 테스트 전용이라 부담은 적어요 |
| `assert.Equal` (`github.com/stretchr/testify`) | PHPUnit `assertEquals` 랑 제일 비슷해요 | 팀마다 쓰는지 안 쓰는지 갈려요 |

기대값을 일부러 틀리게 넣고 두 방법을 같이 돌려 봤어요.

```
price_test.go:31: DeepEqual: got {Subtotal:1000 Discount:100 Total:900}, want {Subtotal:1000 Discount:100 Total:1000}
price_test.go:34: Calc() mismatch (-want +got):
      price.Price{
      	Subtotal: 1000,
      	Discount: 100,
    - 	Total:    1000,
    + 	Total:    900,
      }
```

필드가 많아질수록 `cmp.Diff` 가 편해요. 인자 순서는 `cmp.Diff(want, got)` 로 맞추고 메시지에 `(-want +got)` 을 적는 게 관례예요.

nil 슬라이스와 빈 슬라이스는 `DeepEqual` 도 `cmp.Equal` 도 다르다고 봐요(둘 다 `false`). 03편처럼 JSON에서 `null` 과 `[]` 로 갈리니까 잡아 주는 게 맞을 때가 많고, 상관없을 때만 `cmpopts.EquateEmpty()` 를 붙여요.

## 07. HTTP 핸들러 테스트와 golden 파일

`net/http/httptest` 를 쓰면 서버를 안 띄우고 핸들러 함수를 바로 부를 수 있어요. 요청은 `httptest.NewRequest`, 응답은 `httptest.NewRecorder` 가 받아 둬요.

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

`json.NewEncoder` 는 끝에 줄바꿈을 붙여서 `TrimSpace` 로 떼고 비교해요. 이걸 빼먹으면 눈으로는 똑같은데 실패해요. gin 핸들러도 `gin.CreateTestContext(rec)` 나 라우터의 `ServeHTTP(rec, req)` 로 같은 방식으로 테스트해요.

### golden 파일

응답이 길면 기대값을 표에 다 넣기 힘들어요. 그럴 땐 기대값을 `testdata/xxx.golden` 파일로 두고 비교해요.

```go
var update = flag.Bool("update", false, "golden 파일을 새로 써요")

golden := filepath.Join("testdata", "missing_email.golden")
if *update {
    os.WriteFile(golden, rec.Body.Bytes(), 0o644)
}
want, err := os.ReadFile(golden)
if err != nil {
    t.Fatal(err)
}
if diff := cmp.Diff(string(want), rec.Body.String()); diff != "" {
    t.Errorf("golden mismatch (-want +got):\n%s", diff)
}
```

처음엔 파일이 없어서 실패하고, `go test -run Golden ./web/ -update` 로 한 번 돌리면 파일이 생기고 그다음부터 통과해요. `-update` 로 새로 쓴 파일은 **꼭 diff를 눈으로 보고** 커밋해요.

## 08. PHPUnit, JUnit이랑 비교하면

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

## 09. 조심할 것

- **map 표는 실행 순서가 매번 달라요.** 앞 케이스가 만든 데이터를 뒤 케이스가 쓰면 가끔만 깨지는 테스트가 돼요. 케이스는 서로 독립적으로 만들어요.
- **고루틴 안에서 `t.Fatal` 을 부르면 테스트가 안 멈춰요.** `Fatal` 은 자기를 부른 고루틴만 끝내요. 직접 돌려 보니 고루틴에서 `t.Fatal` 이 찍힌 다음 줄의 `t.Log("테스트 함수는 계속 돌아요")` 까지 실행됐어요. `go vet` 은 `call to (*testing.T).Fatal from a non-test goroutine` 으로 잡아 줘요. 고루틴에서는 `t.Error` 를 쓰거나, 결과를 채널로 받아서 테스트 고루틴에서 판단해요.
- **병렬 케이스끼리 같은 값을 쓰면 레이스가 나요.** 전역 변수 `counter++` 를 `t.Parallel()` 케이스 네 개에서 돌렸더니 `-race` 가 `WARNING: DATA RACE` 와 `race detected during execution of test` 로 실패시켰어요. `-race` 없이는 그냥 통과해요. 공유하는 값은 케이스마다 새로 만들어요.
- **이름 없이 짜면 어느 케이스가 깨졌는지 몰라요.** `t.Run` 없이 for문 안에서 바로 `t.Errorf` 를 부르면 이렇게 나와요. `--- FAIL: TestAdd (0.00s)
 noname_test.go:11: got 4, want 5
 noname_test.go:11: got 10, want 11` 줄 번호가 다 같아서 표의 몇 번째 줄인지 찾아야 해요. 이름에는 "무엇을 확인하는지"를 적어요.

## 10. 스스로 확인해 보기

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

## 11. 참고한 글

- [Go 테스트 코드 작성 및 실행](https://devocean.sk.com/experts/techBoardDetail.do?ID=163605) — SK DEVOCEAN. `_test.go` 규칙, 테이블 주도 테스트로 중복 줄이기
- [TDD로 배우는 Golang](https://velog.io/@tmdgh0221/TDD%EB%A1%9C-%EB%B0%B0%EC%9A%B0%EB%8A%94-Golang) — velog. `t.Run`, `t.Helper`, 익명 struct 슬라이스, `reflect.DeepEqual`
- [GO Test code - 1일차 테스트 코드 작성, coverage 확인 방법](https://velog.io/@chappi/GO-Test-code-1%EC%9D%BC%EC%B0%A8-golang%EC%97%90%EC%84%9C-%ED%85%8C%EC%8A%A4%ED%8A%B8-%EC%BD%94%EB%93%9C-%EC%9E%91%EC%84%B1-coverage-%ED%99%95%EC%9D%B8-%EB%B0%A9%EB%B2%95) — velog. `-cover`, `-coverprofile`, `go tool cover -html`
- [Golang 프로젝트에 TDD 도입하기](https://golangkorea.github.io/post/tdd-with-golang/) — Golang Korea. `httptest` 로 핸들러 테스트하기
- [Go 테스트 자동화: Unit 테스트부터 Integration 테스트까지](https://devocean.sk.com/blog/techBoardDetail.do?ID=167575&boardType=techBlog) — SK DEVOCEAN. testify assert/mock, 테스트 옵션
- [\[Golang\] go 1.22](https://velog.io/@excellent/Golang-go-1.22) — velog. 1.22에서 for문 변수가 반복마다 새로 생기게 바뀐 내용
