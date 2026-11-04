---
title: "05. CodeIgniter 컨트롤러 대신 gin으로 API를 만들면 어떻게 될까?"
date: 2026-11-04
tags: ["Go"]
---

# 05. CodeIgniter 컨트롤러 대신 gin으로 API를 만들면 어떻게 될까?

**Go 학습 · 05**

CodeIgniter 4에서 Routes.php에 경로를 적고, 컨트롤러 메서드에서 `$this->request->getJSON()` 으로 받아 `$this->respond()` 로 돌려주던 흐름을 gin으로 그대로 옮겨 봐요. 게시글 API 하나를 만들면서 라우터, 핸들러, 미들웨어, 바인딩, 에러 응답, 서버 종료까지 짚어요. 예제는 Go 1.26, gin v1.12.0 에서 직접 돌리고 curl로 확인한 결과예요.

| 항목 | 내용 |
|---|---|
| 궁금했던 것 | CI4 컨트롤러로 짜던 API를 gin으로 짜면 뭐가 달라져? |
| 한 줄 답 | 뼈대는 거의 같아요. Routes.php는 `r.GET`·`Group`, 컨트롤러 메서드는 핸들러 함수, Filter는 미들웨어예요. 대신 서버를 켜고 끄는 것까지 내 코드가 맡고, `return` 을 빼먹으면 조용히 이상하게 돌아요. |
| 정리한 날 | 2026-11-04 |
| 같이 볼 글 | Go 학습 내용 · [01. Go 서버는 데몬이 필요 없다](01-실행방식.md) · [02. 고루틴과 스프링](02-goroutine-spring.md) · [03. PHP 7.4와 문법 차이](03-php-문법차이.md) · [06. sqlx와 커넥션 풀](06-sqlx-커넥션풀.md) |

## 01. 한 줄 답: 뼈대는 같고, 책임이 조금 늘어요

CI4로 API를 짜 봤으면 gin은 금방 익숙해져요. 경로를 등록하고, 요청을 받아서, JSON으로 돌려주는 흐름이 똑같거든요. 다른 건 두 가지예요. 프레임워크가 알아서 해 주던 일 몇 개를 내가 직접 챙겨야 하고, 타입이 있어서 요청 값 검사가 struct 태그로 들어가요.

> 💡 gin은 "라우터 + 미들웨어 체인 + 바인딩"만 주는 가벼운 도구예요. CI4의 `ResourceController` 같은 상위 클래스는 없고, 핸들러는 `func(c *gin.Context)` 하나면 끝이에요.

> 📌 그대로 옮겨지는 것\
> **라우트, 컨트롤러, 필터**\
> Routes.php는 `r.GET`·`Group`, 컨트롤러 메서드는 핸들러, Filter는 미들웨어로 1:1 대응돼요.

> 📌 조용히 다르게 도는 것\
> **`c.Abort()`, `required`**\
> Abort해도 함수가 안 끝나고, `required` 는 숫자 0을 "값 없음"으로 봐요.

> 📌 새로 챙겨야 하는 것\
> **서버 종료, 고루틴**\
> PHP-FPM이 하던 프로세스 관리를 내 `main()` 이 해요. 요청 객체를 고루틴에 넘길 땐 복사해요.

## 02. 요청 하나가 지나가는 길

공항 출국장을 떠올리면 쉬워요. 승객(요청)은 체크인 카운터, 보안 검색대를 차례로 지나서 탑승구(핸들러)에 도착해요. 검색대 하나하나가 미들웨어예요. 검색대에서 "통과 불가"가 나오면 승객은 탑승구까지 못 가요. 그게 `c.Abort()` 예요.

```
요청 → gin.Engine (라우터)
       → Recovery   (panic이 나면 500으로 막아 줘요)
       → 로그 미들웨어 (c.Next() 앞: 시작 시각 기록)
       → 인증 미들웨어 (통과 못 하면 c.Abort)
       → 핸들러     (바인딩 → service 호출 → c.JSON)
       ← 로그 미들웨어 (c.Next() 뒤: 걸린 시간, 상태 코드 기록)
응답 ←
```

CI4는 요청마다 PHP-FPM 워커가 `index.php` 부터 다시 시작하죠. gin은 서버가 한 번 떠 있고, 요청이 올 때마다 고루틴 하나가 이 체인을 타요. 핸들러끼리 공유하는 변수는 동시에 건드릴 수 있어요([02편](02-goroutine-spring.md)).

## 03. 라우터와 핸들러 — Routes.php와 컨트롤러

```go
// CI4: app/Config/Routes.php
$routes->group('api/v1/posts', function ($routes) {
    $routes->get('/', 'Posts::index');
    $routes->get('(:num)', 'Posts::show/$1');
    $routes->post('/', 'Posts::create', ['filter' => 'auth']);
});

// gin
v1 := r.Group("/api/v1")
posts := v1.Group("/posts")
posts.GET("", h.List)
posts.GET("/:id", h.Get)                 // (:num) 대신 :id, 숫자 검사는 바인딩에서
w := posts.Group("", Auth())             // 인증 미들웨어를 붙인 하위 그룹
w.POST("", h.Create)
```

핸들러는 struct 메서드로 만들어서 service를 필드로 들고 다녀요. CI4 컨트롤러가 모델을 들고 있던 것과 같아요.

```go
type Handler struct{ svc *Service }

func (h *Handler) Get(c *gin.Context) {
    var u struct {
        ID int64 `uri:"id" binding:"required,min=1"`
    }
    if err := c.ShouldBindUri(&u); err != nil {
        fail(c, http.StatusBadRequest, "INVALID_ID", err.Error())
        return
    }
    p, err := h.svc.Get(c.Request.Context(), u.ID)
    if errors.Is(err, ErrNotFound) {
        fail(c, http.StatusNotFound, "POST_NOT_FOUND", "게시글이 없어요")
        return
    }
    if err != nil {
        fail(c, http.StatusInternalServerError, "INTERNAL", "잠시 후 다시 시도해 주세요")
        return
    }
    c.JSON(http.StatusOK, p)
}
```

```bash
$ curl localhost:18085/api/v1/posts/1
{"id":1,"title":"첫 글","views":0}
$ curl localhost:18085/api/v1/posts/99
{"code":"POST_NOT_FOUND","message":"게시글이 없어요"}            ← 404
$ curl localhost:18085/api/v1/posts/abc
{"code":"INVALID_ID","message":"strconv.ParseInt: parsing \"abc\": invalid syntax"}   ← 400
```

## 04. Filter 대신 미들웨어 — `c.Next()` 와 `c.Abort()`

CI4 Filter는 `before()` 와 `after()` 를 따로 만들죠. gin 미들웨어는 함수 하나 안에서 `c.Next()` 를 기준으로 앞이 before, 뒤가 after예요.

```go
func Timing() gin.HandlerFunc {
    return func(c *gin.Context) {
        start := time.Now()             // before
        c.Next()                        // 다음 미들웨어, 핸들러 실행
        log.Printf("%s -> %d (%s)",     // after
            c.Request.URL.Path, c.Writer.Status(), time.Since(start))
    }
}

func Auth() gin.HandlerFunc {
    return func(c *gin.Context) {
        if c.GetHeader("Authorization") == "" {
            fail(c, http.StatusUnauthorized, "UNAUTHORIZED", "로그인이 필요해요")
            return                      // 꼭 return
        }
        c.Next()
    }
}
```

- **CI4 before()에서 Response를 return하던 자리가 `c.Abort()` 예요.** Abort는 "뒤에 남은 미들웨어와 핸들러를 부르지 마"라는 표시만 남겨요. 지금 돌고 있는 함수는 안 멈춰요. 그래서 바로 `return` 을 붙여요.
- **미들웨어를 붙이는 위치가 세 가지예요.** `r.Use()` 는 전체, `Group("/x", mw)` 는 그룹, `r.GET("/x", mw, h)` 는 경로 하나예요. CI4 Filters.php의 `$globals`, 그룹 `filter` 옵션, 라우트별 `filter` 와 같아요.

## 05. 요청 받기 — `getJSON`, `getVar` 대신 바인딩

CI4는 `$this->request->getJSON(true)` 로 배열을 받고 `$this->validate()` 로 따로 검사하죠. gin은 struct를 하나 만들고 태그에 "어디서 받을지"와 "어떻게 검사할지"를 같이 적어요. 받기와 검사가 한 번에 끝나요.

```go
type CreateReq struct {
    Title string `json:"title" binding:"required,max=100"`   // 'required|max_length[100]'
    Views *int   `json:"views" binding:"required,min=0"`     // 0도 받으려고 포인터
}

type ListQuery struct {
    Page  int `form:"page,default=1"   binding:"min=1"`       // ?page=
    Limit int `form:"limit,default=20" binding:"min=1,max=100"`
}

var req CreateReq
if err := c.ShouldBindJSON(&req); err != nil { /* 400 */ }
var q ListQuery
if err := c.ShouldBindQuery(&q); err != nil { /* 400 */ }
```

| CI4 | gin | 태그 |
|---|---|---|
| `$this->request->getJSON(true)` | `c.ShouldBindJSON(&req)` | `json:"..."` |
| `$this->request->getGet('page')` | `c.ShouldBindQuery(&q)`, 하나만은 `c.Query("page")` | `form:"..."` |
| `Posts::show/$1` 의 `$id` | `c.ShouldBindUri(&u)`, 하나만은 `c.Param("id")` | `uri:"..."` |
| `$this->request->getVar()` | `c.ShouldBind(&x)` | Content-Type 보고 골라요 |
| `$this->validate([...])` | 위 함수들이 같이 해요 | `binding:"..."` |

```bash
$ curl "localhost:18085/api/v1/posts"
{"items":[],"limit":20,"page":1}                        ← default 값이 들어가요
$ curl "localhost:18085/api/v1/posts?limit=500"
{"code":"INVALID_QUERY","message":"Key: 'ListQuery.Limit' Error:Field validation for 'Limit' failed on the 'max' tag"}
```

`Bind`, `BindJSON` (Should가 없는 쪽)도 있어요. 이건 실패하면 gin이 400을 바로 써 버려서 응답 모양을 내가 못 정해요. 에러 응답을 통일하려면 늘 `ShouldBind` 계열을 써요.

## 06. 응답과 에러 응답 — `respond()` 대신 `c.JSON`

CI4 `ResponseTrait` 의 `respond()`, `failNotFound()`, `failValidationErrors()` 같은 건 gin에 없어요. 대신 에러 응답 모양을 정해 두고 작은 함수 하나로 모아요. 핸들러마다 `gin.H{"error": ...}` 를 제각각 쓰면 금방 모양이 흩어져요.

```go
type ErrorBody struct {
    Code    string `json:"code"`
    Message string `json:"message"`
}

func fail(c *gin.Context, status int, code, msg string) {
    c.AbortWithStatusJSON(status, ErrorBody{Code: code, Message: msg})
}
```

- **service는 HTTP 상태 코드를 몰라요.** service는 `fmt.Errorf("post id=%d: %w", id, ErrNotFound)` 처럼 감싼 에러를 돌려주고, 핸들러가 `errors.Is` 로 확인해서 404로 바꿔요([03편 5장](03-php-문법차이.md)).
- **500일 때 `err.Error()` 를 그대로 내보내지 않아요.** SQL이나 내부 경로가 응답에 섞일 수 있어요. 자세한 내용은 로그에 남기고, 응답은 정해 둔 문구만 줘요.
- **핸들러가 많아지면 에러 미들웨어로 모아도 돼요.** 핸들러는 `c.Error(err)` 만 부르고, 미들웨어가 `c.Next()` 뒤에서 `c.Errors` 를 보고 응답을 써요. 스프링의 `@RestControllerAdvice` 와 비슷한 자리예요.

## 07. 서버 켜고 끄기 — `r.Run()` 대신 `http.Server`

[01편](01-실행방식.md)에서 본 것처럼 Go 서버는 실행 파일 하나가 직접 포트를 열어요. PHP-FPM이 워커를 정리해 주던 일을 이제 내 `main()` 이 해요. 예제에 자주 나오는 `r.Run(":8080")` 은 종료 신호를 받으면 처리 중인 요청까지 그냥 끊겨요. 그래서 실서비스는 `http.Server` 로 감싸서 `Shutdown` 을 불러요.

```go
srv := &http.Server{Addr: ":18085", Handler: r}
go func() {
    if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
        log.Fatalf("listen: %v", err)
    }
}()

quit := make(chan os.Signal, 1)
signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
<-quit                                          // 종료 신호가 올 때까지 기다려요

ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()
if err := srv.Shutdown(ctx); err != nil {     // 새 연결은 막고, 처리 중인 요청은 끝까지
    log.Println("shutdown:", err)
}
```

3초 걸리는 `/slow` 요청을 보내 놓고 0.5초 뒤에 `SIGTERM` 을 보내 봤어요.

```
20:04:45 shutdown start
(새 요청)  curl: exit 7                        ← 새 연결은 거절돼요
20:04:48 timing GET /slow -> 200 (3.0s)        ← 처리 중이던 요청은 끝까지 가요
20:04:48 shutdown done
```

단, `Shutdown` 은 핸들러만 기다려요. 핸들러가 띄운 고루틴은 안 기다려요. 그런 작업이 있으면 `sync.WaitGroup` 으로 따로 기다려야 해요.

## 08. 폴더 나누기와 context

```
post/
├─ handler.go      // gin은 여기서만 import. 바인딩, service 호출, 응답
├─ service.go      // 유스케이스, 권한 확인. context.Context만 받아요
├─ repository.go   // 저장소 인터페이스
└─ mysql/
   └─ repository.go // SQL 실행
cmd/api/main.go    // DB 연결 → repository → service → handler 순서로 만들고 라우터 등록
```

- **핸들러는 service에 `c.Request.Context()` 를 넘겨요.** `*gin.Context` 를 넘기면 service가 gin에 묶여서 테스트도 어렵고, 10장의 고루틴 문제도 따라와요.
- **이 context는 클라이언트가 끊으면 취소돼요.** 200ms 뒤에 끊는 클라이언트로 2초짜리 핸들러를 불러 봤더니, 핸들러에서 `ctx.Done()` 이 바로 닫히고 `context canceled` 가 나왔어요. 이 ctx를 DB 쿼리까지 넘기면 아무도 안 기다리는 쿼리를 중간에 멈출 수 있어요.

## 09. CodeIgniter, 스프링과 한눈에 비교

| CodeIgniter 4 | 스프링 | gin |
|---|---|---|
| `app/Config/Routes.php` | `@GetMapping`, `@RequestMapping` | `r.GET`, `r.Group` |
| 컨트롤러 메서드 | `@RestController` 메서드 | `func(c *gin.Context)` |
| Filter `before` / `after` | `HandlerInterceptor`, Filter | 미들웨어, `c.Next()` 앞 / 뒤 |
| before()에서 Response return | `preHandle` 에서 `false` | `c.Abort()` + `return` |
| `getJSON()` + `validate()` | `@RequestBody @Valid` | `ShouldBindJSON` + `binding` 태그 |
| `getGet()`, 라우트 `$1` | `@RequestParam`, `@PathVariable` | `ShouldBindQuery`, `ShouldBindUri` |
| `$this->respond()`, `fail*()` | `ResponseEntity` | `c.JSON`, `c.AbortWithStatusJSON` |
| 예외 + `ExceptionHandler` | `@RestControllerAdvice` | `errors.Is` 로 분기, 또는 에러 미들웨어 |
| PHP-FPM이 프로세스 관리 | `server.shutdown=graceful` | `http.Server.Shutdown` 직접 호출 |
| `CI_ENVIRONMENT` | `spring.profiles.active` | `GIN_MODE=release` |

## 10. 조심할 것

### 1. `c.Abort()` 는 함수를 끝내지 않아요

핸들러에서 Abort 뒤에 `return` 을 빼먹으면 아래 코드가 계속 돌아요. 실제로 돌려 보면 응답이 두 번 붙어서 나가요.

```
if c.Query("id") == "" {
    c.AbortWithStatusJSON(400, gin.H{"error": "id required"})
    // return 빠짐
}
c.JSON(200, gin.H{"ok": true})

// 결과: status=400 body={"error":"id required"}{"ok":true}
```

미들웨어에서 빼먹으면 뒤의 핸들러는 안 불려도, Abort 다음 줄(로그, DB 조회 등)은 실행돼요.

### 2. `binding:"required"` 는 0을 "값 없음"으로 봐요

`Views int` 에 `required` 를 달고 `{"views":0}` 을 보내면 400이 나요. Go는 "안 보냄"과 "0을 보냄"을 구분 못 하거든요([03편](03-php-문법차이.md)의 제로 값). `false`, `""` 도 같아요. 0이 정상 값이면 `*int` 로 받아요.

```
Views int  + required, {"views":0}  → 400 failed on the 'required' tag
Views *int + required, {"views":0}  → 201 {"title":"a","views":0}
Views *int + required, {}           → 400 failed on the 'required' tag
```

### 3. `gin.Context` 를 고루틴에 그대로 넘기지 않아요

gin은 성능 때문에 `gin.Context` 를 `sync.Pool` 로 재활용해요. 응답이 끝나면 같은 객체가 다음 요청에 쓰여요. 그래서 고루틴에서 원래 `c` 를 읽으면 다른 요청을 보게 돼요. 넘길 땐 `c.Copy()` 로 복사해요.

```go
r.GET("/a", func(c *gin.Context) {
    cCp := c.Copy()
    go func() {
        time.Sleep(50 * time.Millisecond)
        log.Println(c.Request.URL.Path, cCp.Request.URL.Path)
    }()
    c.Status(202)
})
// /a 응답 직후 /b 요청을 보내면
// 결과: original c sees "/b", c.Copy sees "/a"   (go test -race 는 DATA RACE로 실패)
```

복사본도 `c.Request.Context()` 는 요청이 끝나면 취소돼요. 응답 뒤에도 돌아야 하는 작업은 필요한 값만 꺼내서 새 context로 시작해요.

### 4. `gin.Default()` 에는 Logger와 Recovery가 들어 있어요

`gin.Default()` 는 `gin.New()` 에 Logger, Recovery 두 개를 붙인 거예요(핸들러 수를 찍어 보면 2와 0). 팀에서 쓰는 로그 미들웨어가 따로 있으면 `gin.New()` 로 시작해야 로그가 두 번 안 찍혀요. Recovery를 빼먹으면 panic이 난 요청은 응답 없이 연결이 끊겨요(curl에는 EOF). 서버 전체가 죽지는 않아요.

### 5. 운영에서는 release 모드로 띄워요

기본 debug 모드는 라우트 목록과 `Running in "debug" mode. Switch to "release" mode in production.` 경고를 찍어요. `GIN_MODE=release` 환경 변수나 `gin.SetMode(gin.ReleaseMode)` 로 바꿔요.

## 11. 스스로 확인해 보기

#### 1. 게시글 수정 API에서 `` IsPinned bool `json:"is_pinned" binding:"required"` `` 로 받았어요. 고정을 풀려고 `{"is_pinned": false}` 를 보내면 어떻게 될까?

<details>
<summary>답 보기</summary>

400이 나요. `false` 는 bool의 제로 값이라서 `required` 가 "값 없음"으로 봐요. 고정을 켜는 건 되는데 끄는 것만 안 되는 이상한 버그가 돼요. `*bool` 로 받으면 "안 보냄(nil)"과 "false"를 구분할 수 있어요.

</details>

#### 2. 게시글을 저장한 뒤 알림 발송을 `go sendNotice(c)` 로 뒤에서 돌렸어요. 로컬에서는 잘 되는데 운영에서 가끔 다른 사람 글로 알림이 간다면 왜일까?

<details>
<summary>답 보기</summary>

핸들러가 끝나면 gin이 그 `gin.Context` 를 다음 요청에 재활용해요. 고루틴이 늦게 `c` 를 읽으면 다른 요청의 값을 보게 돼요. 요청이 적은 로컬에서는 재활용이 잘 안 일어나서 안 보여요. 필요한 값(게시글 ID 등)만 꺼내서 넘기거나 `c.Copy()` 를 넘겨요.

</details>

## 12. 참고한 글

- [미들웨어](https://gin-gonic.com/ko-kr/docs/middleware/) — gin 공식 문서(한국어). `c.Next()` 앞뒤로 나뉘는 양파 구조, 미들웨어를 붙이는 범위
- [미들웨어 내 고루틴](https://gin-gonic.com/ko-kr/docs/middleware/goroutines-inside-a-middleware/) — gin 공식 문서(한국어). `sync.Pool` 재활용과 `c.Copy()`
- [Graceful Restart or Stop](https://gin-gonic.com/ko-kr/docs/server-config/graceful-restart-or-stop/) — gin 공식 문서(한국어). `http.Server.Shutdown` 예제
- [Gin](https://velog.io/@connor/Gin) — velog. 라우팅, 바인딩, 렌더링, 미들웨어, 서버 설정을 예제로 한 번에 훑기
- [\[Golang\] ShouldBindJson 와 BindJSON](https://velog.io/@imsooyeon/Golang-ShouldBindJson-%EC%99%80-BindJSON) — velog. 스프링 `@RequestBody` 와 비교
- [\[go/gin\] 요청 Validation에 대해 알아보자](https://velog.io/@beardfriend/gogin-%EC%9A%94%EC%B2%AD-Validation%EC%97%90-%EB%8C%80%ED%95%B4-%EC%95%8C%EC%95%84%EB%B3%B4%EC%9E%90) — velog. `required`, `min`/`max`, `oneof`, 커스텀 검사 등록
- [Graceful shutdown?](https://velog.io/@smoothbear/graceful-shutdown) — velog. gin + `http.Server` 로 SIGINT/SIGTERM 처리
