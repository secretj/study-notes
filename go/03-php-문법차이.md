---
title: "03. PHP 7.4만 하다가 Go 문법을 보면 뭐가 다를까?"
date: 2026-11-04
tags: ["Go"]
---

# 03. PHP 7.4만 하다가 Go 문법을 보면 뭐가 다를까?

**Go 학습 · 03**

PHP로 짜던 습관 그대로 Go를 짜면 컴파일이 안 되거나, 컴파일은 되는데 다르게 돌아가는 곳이 있어요. 문법 설명서처럼 다 훑지 않고, PHP 7.4 개발자가 실제로 걸려 넘어지는 곳만 골라서 정리해요. 예제는 PHP 7.4.33, Go 1.26 에서 직접 돌려 본 결과예요.

| 항목 | 내용 |
|---|---|
| 궁금했던 것 | 문법이 PHP 7.4랑 뭐가 달라? |
| 한 줄 답 | PHP는 "일단 돌려 보고 알아서 맞춰 주는" 언어고, Go는 "컴파일할 때 다 정해 두는" 언어예요. 타입, 배열, 에러, 클래스 네 군데가 제일 많이 달라요. |
| 정리한 날 | 2026-11-04 |
| 같이 볼 글 | [Go 학습 내용](https://wiki.mailplug.co.kr/confluence/pages/viewpage.action?pageId=224339879) · [04. 자주 쓰는 함수 대응표](https://wiki.mailplug.co.kr/confluence/pages/viewpage.action?pageId=224340555) |

## 01. 한 줄 답: PHP가 알아서 해 주던 걸 Go는 안 해 줘요

PHP는 `"1" + 1` 을 알아서 `2` 로 만들어 주고, 없는 배열 키를 읽어도 경고만 띄우고 넘어가요. Go는 이런 걸 하나도 안 해 줘요. 대신 실수 대부분을 **실행하기 전에** 컴파일러가 잡아 줘요.

> 💡 PHP에서 런타임에 터지던 실수가 Go에서는 빌드할 때 빨간 줄로 나와요. 처음엔 귀찮고, 익숙해지면 편해요.

> 📌 제일 많이 걸리는 곳\
> **타입이랑 형변환**\
> `$` 가 없고, 타입이 다르면 더하기도 비교도 안 돼요. 자동 형변환이 없어요.

> 📌 조용히 다르게 도는 곳\
> **배열, map, 슬라이스**\
> 컴파일은 되는데 순서가 바뀌거나 원본이 같이 바뀌어요. 제일 위험해요.

> 📌 생각을 바꿔야 하는 곳\
> **클래스, 예외**\
> class, extends, try/catch가 없어요. struct, 인터페이스, `if err != nil` 로 바뀌어요.

## 02. 변수와 타입

### 선언은 `:=` 하나면 돼요

```go
// PHP 7.4
$name = "jin";
$count = 0;

// Go
name := "jin"        // 타입은 알아서 string으로 정해져요
var count int        // 값을 안 주면 0 이 들어가요
count = "hello"      // 컴파일 에러: string을 int에 못 넣어요
```

- **`$` 가 없어요.** 처음 만들 때는 `:=`, 이미 있는 변수에 넣을 때는 `=` 예요. 함수 밖(패키지 레벨)에서는 `:=` 를 못 쓰고 `var` 를 써야 해요.
- **한번 정한 타입은 안 바뀌어요.** PHP 7.4의 타입 힌트(`int $id`)는 함수 인자에만 붙지만, Go는 모든 변수에 타입이 있어요.
- **안 쓰는 변수, 안 쓰는 import는 컴파일 에러예요.** 경고가 아니라 에러라서 빌드가 안 돼요. 일부러 버릴 땐 `_` 에 받아요.

### null 대신 "제로 값"이 있어요

Go는 변수를 만들면 무조건 그 타입의 기본값(제로 값)이 들어가요. 숫자는 `0`, 문자열은 `""`, bool은 `false` 예요. 포인터, 슬라이스, map, 인터페이스만 `nil` 이 될 수 있어요.

그래서 PHP 7.4의 `?int` (null 가능한 int)를 Go로 옮기면 고민이 생겨요. "0"이랑 "값 없음"을 구분해야 하면 `*int` (포인터)나 `sql.NullInt64` 를 써요.

### 자동 형변환이 없어요

```go
// PHP 7.4 — 실제로 돌려 본 결과
"1" + 1        // 2
"abc" == 0     // true  (PHP 8부터는 false)
intval("12abc") // 12

// Go
"1" + 1                  // 컴파일 에러
n, err := strconv.Atoi("12abc")  // n=0, err="invalid syntax"
```

Go에는 `===` 가 없어요. 필요가 없어서예요. 타입이 다르면 `==` 로 비교 자체를 못 하니까, Go의 `==` 는 늘 PHP의 `===` 처럼 동작해요.

## 03. PHP array 하나가 Go에서는 셋으로 나뉘어요

PHP의 `array` 는 리스트도 되고, 연관 배열(해시)도 되고, 대충 객체 대신으로도 써요. Go에서는 용도마다 따로 있어요.

| PHP에서 이렇게 쓰던 것 | Go에서는 | 예시 |
|---|---|---|
| `[1, 2, 3]` 순서 있는 목록 | **슬라이스** `[]int` | `ids := []int{1, 2, 3}` |
| `['a' => 1]` 키-값 | **map** `map[string]int` | `m := map[string]int{"a": 1}` |
| `['id' => 1, 'name' => 'jin']` 필드 묶음 | **struct** | `User{ID: 1, Name: "jin"}` |

### 조심 1. map은 순서가 없어요

PHP 배열은 넣은 순서를 기억해요. Go map은 **일부러** 돌릴 때마다 순서를 섞어요. 순서에 기대는 코드를 처음부터 못 짜게 하려는 거예요. 순서가 필요하면 키를 뽑아서 정렬해요.

```go
// PHP: 넣은 순서 그대로 {"b":1,"a":2}
// Go: for range 순서는 매번 달라요

keys := slices.Sorted(maps.Keys(m))  // Go 1.23+
for _, k := range keys {
    fmt.Println(k, m[k])
}
```

참고로 `json.Marshal` 은 map 키를 알파벳 순으로 정렬해서 내보내요. `{"b":1,"a":2}` 를 넣으면 `{"a":2,"b":1}` 이 나와요. 응답 필드 순서를 지키고 싶으면 map 말고 struct를 써요.

### 조심 2. 없는 키를 읽어도 에러가 안 나요

PHP는 `isset($m['k'])` 로 확인하죠. Go는 없는 키를 읽으면 그냥 제로 값(`0`, `""`)이 나와요. "0이 들어 있는 것"이랑 "없는 것"을 구분하려면 두 번째 값을 받아요.

```go
v, ok := m["zzz"]   // v=0, ok=false
if !ok { /* 없어요 */ }
```

### 조심 3. 슬라이스는 복사해도 원본을 같이 써요

PHP 배열은 다른 변수에 넣거나 함수에 넘기면 **복사**돼요. 한쪽을 고쳐도 다른 쪽은 그대로예요. Go 슬라이스는 "배열을 가리키는 창문"이라서, 잘라 낸 슬라이스에 `append` 하면 원본이 바뀔 수 있어요.

```go
a := []int{1, 2, 3, 4}
b := a[:2]          // [1 2] — a랑 같은 배열을 봐요
b = append(b, 99)   // 자리가 남아서 a의 3번째 칸을 덮어써요
fmt.Println(a)      // [1 2 99 4]  ← 원본이 바뀌었어요
```

원본을 지켜야 하면 `slices.Clone(a[:2])` 로 복사본을 만들어서 써요. 그리고 `append` 결과는 늘 다시 변수에 넣어요(`s = append(s, x)`).

### 조심 4. 빈 목록이 JSON에서 `null` 이 될 수 있어요

PHP `json_encode([])` 는 `[]` 예요. Go는 선언만 한 슬라이스(`nil`)를 넣으면 `null` 이 나와요. 목록 API의 `"value"` 가 `null` 로 나가면 프론트에서 `.map()` 이 터지니까, 빈 목록은 `[]Item{}` 로 만들어서 넣어요.

```go
var items []int                    // {"value":null}
items := []int{}                   // {"value":[]}
```

## 04. 클래스 대신 struct와 인터페이스

```go
// PHP 7.4
class UserService {
    private UserRepository $repo;
    public function __construct(UserRepository $repo) { $this->repo = $repo; }
    public function find(int $id): ?User { return $this->repo->find($id); }
}

// Go
type UserService struct {
    repo UserRepository        // 소문자 = 패키지 밖에서 못 봐요 (private)
}

func NewUserService(repo UserRepository) *UserService {  // 생성자 대신 New 함수
    return &UserService{repo: repo}
}

func (s *UserService) Find(ctx context.Context, id int64) (*User, error) {  // 대문자 = public
    return s.repo.Find(ctx, id)
}
```

- **public/private 대신 첫 글자 대소문자예요.** `Find` 는 밖에서 보이고 `find` 는 안 보여요. 범위도 클래스가 아니라 **패키지** 단위예요. 같은 패키지 안에서는 소문자 필드도 다 보여요.
- **생성자가 없어요.** `NewXxx()` 함수를 만들어 쓰는 게 관례예요.
- **`$this` 대신 리시버예요.** `func (s *UserService)` 의 `s` 가 `$this` 역할이에요. 필드를 바꾸는 메서드는 포인터(`*`)로 받아요.
- **상속(`extends`)이 없어요.** 다른 struct를 필드처럼 끼워 넣는 임베딩으로 메서드를 물려받아요. 다만 "부모-자식"이 아니라 "안에 들고 있는" 관계예요.
- **`implements` 를 안 써요.** 인터페이스의 메서드를 다 갖고 있으면 자동으로 그 인터페이스가 돼요. 그래서 인터페이스는 쓰는 쪽(서비스)에서 필요한 메서드만 골라 정의해요.

namespace는 package, `use` 는 `import`, composer는 `go mod` 에 대응돼요. 다만 PHP처럼 한 파일에 클래스 하나가 아니라 **폴더 하나가 패키지 하나**예요.

## 05. try/catch 대신 `if err != nil`

Go에는 예외가 없어요. 실패할 수 있는 함수는 마지막 반환값으로 `error` 를 돌려주고, 부르는 쪽이 바로 확인해요. 코드에 `if err != nil` 이 줄줄이 나오는 이유가 이거예요.

```go
// PHP 7.4
try {
    $user = $repo->find($id);
} catch (NotFoundException $e) {
    return null;
}

// Go
user, err := repo.Find(ctx, id)
if errors.Is(err, ErrNotFound) {         // catch (NotFoundException) 대신
    return nil, nil
}
if err != nil {
    return nil, fmt.Errorf("find user %d: %w", id, err)  // 감싸서 위로 올려요
}
```

- **`%w` 로 감싸요.** 에러에 "어디서 났는지"를 붙여서 위로 올려요. `%w` 로 감싸야 위에서 `errors.Is` 로 원래 에러를 찾을 수 있어요. `%v` 로 감싸면 연결이 끊겨요.
- **에러 문자열로 비교하지 않아요.** 값 비교는 `errors.Is`, 타입 꺼내기는 `errors.As` 예요.
- **`finally` 대신 `defer` 예요.** `defer f.Close()` 라고 써 두면 함수가 어떻게 끝나든 마지막에 실행돼요.
- **`panic` 은 예외 대용이 아니에요.** "프로그램이 더 돌면 안 되는" 버그 상황에만 써요. 핸들러에서 panic이 나면 gin의 Recovery 미들웨어가 500으로 막아 줘요.

## 06. 문자열

- **따옴표 뜻이 달라요.** `"..."` 는 문자열, `'a'` 는 문자 하나(rune), 백틱 `` `...` `` 은 이스케이프 없는 문자열이에요. PHP처럼 작은따옴표 문자열은 없어요.
- **변수 끼워 넣기가 없어요.** `"Hello $name"` 대신 `fmt.Sprintf("Hello %s", name)` 을 써요.
- **이어 붙이기는 `.` 대신 `+` 예요.** 반복문에서 계속 붙일 땐 `strings.Builder` 를 써요.
- **길이는 바이트 기준이에요.** 이건 PHP랑 같아요. `len("한글")` 은 `strlen` 처럼 6이에요. 글자 수는 `mb_strlen` 대신 `utf8.RuneCountInString` 이에요.
- **문자열은 못 고쳐요.** `s[0] = 'A'` 가 안 돼요. 바꾸려면 새 문자열을 만들어요.

## 07. 반복문, switch, 클로저

### 반복문은 `for` 하나예요

```go
for i := 0; i < 10; i++ { }      // for
for cond { }                      // while
for { }                           // while (true)
for i, v := range items { }       // foreach ($items as $i => $v)
for k, v := range m { }           // foreach ($m as $k => $v) — 순서는 매번 달라요
for i := range 10 { }             // 0~9 (Go 1.22+)
```

### switch는 break가 자동이에요

PHP는 `break` 를 빼먹으면 다음 case로 흘러가요. Go는 반대로 case 하나만 실행하고 끝나요. 다음으로 넘기고 싶을 때만 `fallthrough` 를 적어요. 그리고 PHP switch는 느슨한 비교(`==`)라서 `switch ("1")` 이 `case 1` 에 걸리지만, Go는 타입이 다르면 컴파일이 안 돼요.

### 클로저는 변수를 "참조"해요

PHP 7.4의 화살표 함수 `fn() => $x + 1` 은 만든 순간의 `$x` 값을 복사해 가요. Go 클로저는 변수 자체를 들고 가요. 그래서 나중에 `x` 를 바꾸면 클로저 결과도 바뀌어요. PHP의 `function() use (&$x)` 랑 같아요.

```go
// PHP 7.4: $x = 1; $f = fn() => $x + 1; $x = 10; echo $f();   // 2
// Go:      x := 1;  f := func() int { return x + 1 }; x = 10    // f() == 11
```

옛날 Go(1.21까지)는 for문 변수 하나를 모든 반복이 같이 써서, 고루틴에서 마지막 값만 찍히는 버그가 유명했어요. Go 1.22부터는 반복마다 변수가 새로 생겨서 이 문제가 없어요. 단, `go.mod` 의 go 버전이 1.22 이상이어야 해요.

## 08. 한눈에 비교

| PHP 7.4 | Go | 한마디 |
|---|---|---|
| `$x = 1;` | `x := 1` | 세미콜론도 안 써요 |
| `?int`, `null` | `*int`, `nil`, 제로 값 | 기본은 null이 아니라 0, "" |
| `===` | `==` | 타입 다르면 비교 자체가 안 돼요 |
| `array` | 슬라이스, map, struct | map은 순서 없음 |
| `class`, `extends`, `implements` | `struct`, 임베딩, 암묵적 인터페이스 | 상속 없음 |
| `public` / `private` | 대문자 / 소문자 | 범위는 패키지 |
| `__construct` | `NewXxx()` 함수 | 관례예요 |
| `try` / `catch` / `finally` | `if err != nil` / `errors.Is` / `defer` | 에러는 값이에요 |
| `"Hi $name"`, `.` | `fmt.Sprintf`, `+` | 보간 없음 |
| `foreach`, `while` | `for range`, `for` | 반복문은 for 하나 |
| `namespace`, `use`, composer | `package`, `import`, `go mod` | 폴더 = 패키지 |
| 제네릭 없음 (PHPDoc으로 흉내) | 제네릭 있음 (Go 1.18+) | `func Map[T any](...)` |

반대로 PHP 8에서 생긴 것 중 Go에 없는 것도 있어요. `match`, nullsafe `?->`, named arguments, 기본값 있는 인자는 Go에 없어요. 함수 인자 기본값이 필요하면 옵션 struct를 넘기는 식으로 해결해요.

## 09. 스스로 확인해 보기

#### 1. 메일 목록 API에서 검색 결과가 없을 때 `var list []Mail` 그대로 응답에 넣었어요. PHP 때랑 응답이 어떻게 달라질까?

<details>
<summary>답 보기</summary>

PHP는 빈 배열이 `"value": []` 로 나갔지만, Go는 `nil` 슬라이스라서 `"value": null` 이 나가요. 프론트가 `value.map()` 을 부르면 터져요. `list := []Mail{}` 로 만들거나, 응답 만들 때 `nil` 이면 빈 슬라이스로 바꿔 줘요.

</details>

#### 2. 설정 값을 `map[string]string` 에 담아 for range로 돌면서 화면에 찍었어요. 테스트 서버에서는 순서가 맞았는데 운영에서 순서가 바뀌었다면 왜일까?

<details>
<summary>답 보기</summary>

Go map은 일부러 순회 순서를 섞어요. 테스트에서 맞은 건 우연이에요. 순서가 필요하면 `slices.Sorted(maps.Keys(m))` 로 키를 정렬해서 돌거나, 처음부터 슬라이스로 들고 있어요.

</details>

## 10. 참고한 글

- [Go의 주요 특징들](https://golangkorea.github.io/post/go-start/feature/) — Golang Korea. 대소문자로 공개 범위를 정하는 규칙, struct
- [Golang 기초 (13) : 슬라이스에 대하여](https://velog.io/@vamos_eon/go-slice) — velog. 슬라이스가 배열을 공유해서 append가 원본을 바꾸는 예제
- [Golang 기초 (11) : 문자열에 대하여](https://velog.io/@vamos_eon/go-string) — velog. 바이트, rune
- [Go를 배워보자 8일차 - map](https://velog.io/@chappi/Go%EB%A5%BC-%EB%B0%B0%EC%9B%8C%EB%B3%B4%EC%9E%90-8%EC%9D%BC%EC%B0%A8-map) — velog
- [Go 언어 - OOP 흉내 내기](https://velog.io/@kineo2k/Go-%EC%96%B8%EC%96%B4-OOP-%ED%9D%89%EB%82%B4-%EB%82%B4%EA%B8%B0) — velog. 상속 대신 임베딩, 인터페이스로 다형성
- [Go에서의 덕타이핑](https://velog.io/@myong/Go%EC%97%90%EC%84%9C%EC%9D%98-%EB%8D%95%ED%83%80%EC%9D%B4%ED%95%91) — velog. implements 없이 인터페이스를 만족하는 구조적 타이핑
- [Golang 기초 (10) : 포인터에 대하여](https://velog.io/@vamos_eon/go-pointer) — velog. 제로 값과 nil
- [\[GO\] #3-2. 패키지 탐방 (errors, sort)](https://velog.io/@whdnjsdyd111/GO-3-2.-%ED%8C%A8%ED%82%A4%EC%A7%80-%ED%83%90%EB%B0%A9-errors) — velog. `%w` 로 감싸기, `errors.Is` / `errors.As`
- [golang 에러처리에 대한 고민과 opaque 에러로 똑똑하게 처리하기](https://devocean.sk.com/blog/techBoardDetail.do?ID=166104&boardType=techBlog) — SK DEVOCEAN

메일솔루션 1파트 박진형 · Go 학습 · PHP 7.4와 Go 문법 차이
