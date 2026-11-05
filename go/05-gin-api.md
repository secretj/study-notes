---
title: "05. CodeIgniter 컨트롤러 대신 gin으로 API를 만들면 어떻게 될까?"
date: 2026-11-04
tags: ["Go"]
---

# 05. CodeIgniter 컨트롤러 대신 gin으로 API를 만들면 어떻게 될까?

**Go 학습 · 05**

CodeIgniter 4에서 Routes.php에 경로를 적고, 컨트롤러 메서드에서 `$this->request->getJSON()` 으로 받아 `$this->respond()` 로 돌려주던 흐름을 gin으로 그대로 옮겨 봐요. 가장 작은 서버를 먼저 띄우고, 게시글 API 하나를 조금씩 키우면서 라우터, 핸들러, 미들웨어, 바인딩, 에러 응답, 서버 종료를 차례로 붙여요. 예제는 Go 1.26, gin v1.12.0 에서 직접 돌리고 curl로 확인한 결과예요.

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

## 03. 만들어 볼 것: 게시글 API

여기서부터는 게시글 API 하나를 조금씩 키우면서 볼게요. 먼저 gin이 얼마나 가벼운지 가장 작은 서버부터 띄워 봐요.

### 1단계: 가장 작은 gin 서버

빈 폴더에서 모듈을 만들고 gin을 받아요. CI4에서 `composer require` 하던 자리예요.

```
mkdir hello && cd hello
go mod init example.com/hello
go get github.com/gin-gonic/gin@v1.12.0
```

`main.go` 하나에 경로 하나를 적어요. Routes.php 한 줄과 컨트롤러 메서드 하나를 한 파일에 쓴 셈이에요.

```go
package main

import "github.com/gin-gonic/gin"

func main() {
    r := gin.Default() // 로그·panic 복구 미들웨어가 붙은 라우터

    r.GET("/ping", func(c *gin.Context) { // Routes.php 한 줄 + 컨트롤러 메서드 하나
        c.JSON(200, gin.H{"message": "pong"})
    })

    r.Run(":18085") // 포트를 직접 열어요. php-fpm, nginx 없이 이걸로 끝
}
```

`go run .` 으로 띄우고, 다른 터미널에서 curl을 보내 봤어요.

```bash
$ curl localhost:18085/ping
{"message":"pong"}
```

서버 쪽 터미널에는 이런 로그가 나와요. 눈여겨볼 줄에 `←` 를 달았어요.

```
[GIN-debug] [WARNING] Running in "debug" mode. Switch to "release" mode in production.   ← 11장 5번
[GIN-debug] GET    /ping    --> main.main.func1 (3 handlers)   ← Logger, Recovery, 내 핸들러 (11장 4번)
[GIN-debug] Listening and serving HTTP on :18085   ← nginx, php-fpm 없이 프로세스가 직접 포트를 열어요
[GIN] 2026/11/05 - 14:46:44 | 200 | 108.25µs | ::1 | GET "/ping"
```

경고 두 줄은 지금은 넘어가도 돼요. 11장에서 왜 나오는지 다시 봐요.

### 2단계: 이번 글에서 키울 게시글 API

이 서버를 CI4로 짜던 게시글 API 모양으로 키워요. 경로는 세 개예요.

| 요청 | 하는 일 | CI4로 치면 |
|---|---|---|
| `GET /api/v1/posts` | 목록. `?page`, `?limit` 를 받아요 | `Posts::index` |
| `GET /api/v1/posts/:id` | 글 하나 조회 | `Posts::show/$1` |
| `POST /api/v1/posts` | 글쓰기. 로그인해야 돼요 | `Posts::create` + `auth` 필터 |

DB는 [06편](06-sqlx-커넥션풀.md)에서 붙여요. 이번 글은 HTTP 쪽만 보려고 게시글을 메모리에 둬요. CI4 모델이 있던 자리에 들어가는 `Service` 는 이 정도예요.

```go
type Post struct {
    ID    int64  `json:"id"`
    Title string `json:"title"`
    Views int    `json:"views"`
}

var ErrNotFound = errors.New("not found")

type Service struct {
    mu     sync.Mutex
    nextID int64
    posts  map[int64]Post
}

func (s *Service) Get(ctx context.Context, id int64) (Post, error) {
    s.mu.Lock()
    defer s.mu.Unlock()
    p, ok := s.posts[id]
    if !ok {
        return Post{}, fmt.Errorf("post id=%d: %w", id, ErrNotFound)
    }
    return p, nil
}

// List, Create 도 같은 모양이에요. 전체 코드는 08장 끝에 있어요.
```

없는 글이면 `ErrNotFound` 를 감싸서 돌려줘요. 이걸 404로 바꾸는 건 핸들러 몫이에요(04장, 07장).

에러 응답에 쓸 도우미 함수도 하나 미리 만들어요. 아래 예제에서 계속 나와요. 왜 이렇게 한 곳에 모으는지는 07장에서 봐요.

```go
type ErrorBody struct {
    Code    string `json:"code"`
    Message string `json:"message"`
}

func fail(c *gin.Context status int, code, msg string) {
    c.AbortWithStatusJSON(status, ErrorBody{Code: code, Message: msg})
}
```

이제 이 위에 라우터(04장), 미들웨어(05장), 바인딩(06장), 서버 종료(08장)를 차례로 붙여요. 장마다 붙인 조각은 08장 끝 "전체 코드"에 한 파일로 모여 있어요.

## 04. 라우터와 핸들러 — Routes.php와 컨트롤러

먼저 경로를 등록해요. 위는 CI4 Routes.php에 적던 것, 아래는 같은 경로를 gin으로 옮긴 거예요. 그룹을 만들고 그 안에 경로를 다는 모양이 거의 같아요.

```go
// CI4: app/Config/Routes.php
$routes->group('api/v1/posts', function ($routes) {
    $routes->get('/', 'Posts::index');
    $routes->get('(:num)', 'Posts::show/$1');
    $routes->post('/', 'Posts::create', ['filter' => 'auth']);
});

// gin
r := gin.New()
r.Use(gin.Recovery(), Timing())   // 모든 요청에 붙는 미들웨어 (05장)

posts := r.Group("/api/v1/posts")
posts.GET("", h.List)
posts.GET("/:id", h.Get)           // (:num) 대신 :id, 숫자 검사는 바인딩에서

w := posts.Group("", Auth())       // 인증 미들웨어를 붙인 하위 그룹
w.POST("", h.Create)
```

`h.List`, `h.Get`, `h.Create` 가 컨트롤러 메서드 자리예요. 핸들러는 struct 메서드로 만들고, 03장에서 만든 `Service` 를 필드로 들고 다녀요. CI4 컨트롤러가 모델을 들고 있던 것과 같아요. 글 하나를 조회하는 `Get` 을 볼게요.

```go
type Handler struct{ svc *Service }

func (h *Handler) Get(c *gin.Context) {
    var u struct {
        ID int64 `uri:"id" binding:"required,min=1"`
    }
    // ① 경로의 :id 를 숫자로 받아요 (06장)
    if err := c.ShouldBindUri(&u); err != nil {
        fail(c, http.StatusBadRequest, "INVALID_ID", err.Error())
        return
    }
    // ② 실제 일은 service에 맡기고, ③ 에러 종류에 따라 상태 코드를 골라요
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

서버를 띄우고 세 가지로 불러 봤어요. 있는 글, 없는 글, 숫자가 아닌 id예요. 끝의 `←` 는 HTTP 상태 코드예요.

```bash
$ curl localhost:18085/api/v1/posts/1
{"id":1,"title":"첫 글","views":0}

$ curl localhost:18085/api/v1/posts/99
{"code":"POST_NOT_FOUND","message":"게시글이 없어요"}  ← 404

$ curl localhost:18085/api/v1/posts/abc
{"code":"INVALID_ID","message":"strconv.ParseInt: parsing \"abc\": invalid syntax"}  ← 400
```

- **99번:** service가 돌려준 `ErrNotFound` 를 핸들러가 `errors.Is` 로 알아보고 404로 바꿨어요.
- **abc:** service까지 가지도 못하고 ①의 바인딩에서 400으로 끝났어요. CI4 라우트의 `(:num)` 이 하던 검사를 바인딩이 해요. 메시지가 Go 에러 문구 그대로라서, 실서비스에서는 사용자에게 보여 줄 문구를 따로 정해요.

## 05. Filter 대신 미들웨어 — `c.Next()` 와 `c.Abort()`

CI4 Filter는 `before()` 와 `after()` 를 따로 만들죠. gin 미들웨어는 함수 하나 안에서 `c.Next()` 를 기준으로 앞이 before, 뒤가 after예요.

게시글 API에는 두 개를 붙여요. 모든 요청의 처리 시간을 찍는 `Timing`, 글쓰기에만 붙는 `Auth` 예요. `Auth` 는 예제라서 `Authorization` 헤더가 있는지만 봐요.

```go
func Timing() gin.HandlerFunc {
    return func(c *gin.Context) {
        start := time.Now()
        c.Next() // 다음 미들웨어, 핸들러 실행
        log.Printf("%s %s -> %d (%s)", c.Request.Method, c.Request.URL.Path,
            c.Writer.Status(), time.Since(start).Round(time.Millisecond))
    }
}

func Auth() gin.HandlerFunc {
    return func(c *gin.Context) {
        if c.GetHeader("Authorization") == "" {
            fail(c, http.StatusUnauthorized, "UNAUTHORIZED", "로그인이 필요해요")
            return // 꼭 return
        }
        c.Next()
    }
}
```

04장 라우터에서 `Timing` 은 `r.Use` 로 전체에, `Auth` 는 `w` 그룹에만 붙였어요. 토큰 없이 글쓰기를 보내고, 토큰을 넣어 다시 보내 봤어요.

```bash
$ curl -X POST localhost:18085/api/v1/posts -d '{"title":"둘째 글","views":0}'
{"code":"UNAUTHORIZED","message":"로그인이 필요해요"}  ← 401

$ curl -X POST localhost:18085/api/v1/posts -H 'Authorization: Bearer t' -d '{"title":"둘째 글","views":0}'
{"id":2,"title":"둘째 글","views":0}  ← 201
```

서버 로그에는 `Timing` 이 `c.Next()` 뒤에서 찍은 줄이 남아요.

```
2026/11/05 14:46:29 POST /api/v1/posts -> 401 (0s)   ← Auth에서 막힌 요청도 찍혀요
2026/11/05 14:46:29 POST /api/v1/posts -> 201 (0s)
```

401로 막힌 요청도 로그가 남은 이유가 있어요. `Auth` 가 Abort 해도, 그보다 앞에서 `c.Next()` 를 부른 `Timing` 은 뒷부분을 마저 실행해요. 공항으로 치면 보안 검색대에서 돌아 나와도 체크인 카운터는 다시 지나가는 셈이에요.

- **CI4 before()에서 Response를 return하던 자리가 `c.Abort()` 예요.** Abort는 "뒤에 남은 미들웨어와 핸들러를 부르지 마"라는 표시만 남겨요. 지금 돌고 있는 함수는 안 멈춰요. 그래서 바로 `return` 을 붙여요(11장 1번).
- **미들웨어를 붙이는 위치가 세 가지예요.** `r.Use()` 는 전체, `Group("/x", mw)` 는 그룹, `r.GET("/x", mw, h)` 는 경로 하나예요. CI4 Filters.php의 `$globals`, 그룹 `filter` 옵션, 라우트별 `filter` 와 같아요.

## 06. 요청 받기 — `getJSON`, `getVar` 대신 바인딩

CI4는 `$this->request->getJSON(true)` 로 배열을 받고 `$this->validate()` 로 따로 검사하죠. gin은 struct를 하나 만들고, 태그에 "어디서 받을지"와 "어떻게 검사할지"를 같이 적어요. 받기와 검사가 한 번에 끝나요.

게시글 API에서는 목록의 쿼리스트링과 글쓰기의 JSON 본문을 struct로 받아요. 목록 핸들러 `List` 가 쓰는 모습까지 같이 봐요.

```go
type ListQuery struct {
    Page  int `form:"page,default=1"   binding:"min=1"` // ?page=
    Limit int `form:"limit,default=20" binding:"min=1,max=100"`
}

type CreateReq struct {
    Title string `json:"title" binding:"required,max=100"` // 'required|max_length[100]'
    Views *int   `json:"views" binding:"required,min=0"`   // 0도 받으려고 포인터 (11장)
}

func (h *Handler) List(c *gin.Context) {
    var q ListQuery
    if err := c.ShouldBindQuery(&q); err != nil {
        fail(c, http.StatusBadRequest, "INVALID_QUERY", err.Error())
        return
    }
    items := h.svc.List(c.Request.Context(), q.Page, q.Limit)
    c.JSON(http.StatusOK, gin.H{"items": items, "page": q.Page, "limit": q.Limit})
}
```

어디서 받느냐에 따라 태그와 함수가 달라요. CI4에서 쓰던 것과 나란히 놓으면 이래요.

| CI4 | gin | 태그 |
|---|---|---|
| `$this->request->getJSON(true)` | `c.ShouldBindJSON(&req)` | `json:"..."` |
| `$this->request->getGet('page')` | `c.ShouldBindQuery(&q)`, 하나만은 `c.Query("page")` | `form:"..."` |
| `Posts::show/$1` 의 `$id` | `c.ShouldBindUri(&u)`, 하나만은 `c.Param("id")` | `uri:"..."` |
| `$this->request->getVar()` | `c.ShouldBind(&x)` | Content-Type 보고 골라요 |
| `$this->validate([...])` | 위 함수들이 같이 해요 | `binding:"..."` |

목록을 세 가지로 불러 봤어요. 아무것도 안 줬을 때, `limit=1`, 범위를 넘는 `limit=500` 이에요.

```bash
$ curl "localhost:18085/api/v1/posts"
{"items":[{"id":1,"title":"첫 글","views":0},{"id":2,"title":"둘째 글","views":0}],"limit":20,"page":1}   ← default 값이 들어가요

$ curl "localhost:18085/api/v1/posts?page=1&limit=1"
{"items":[{"id":1,"title":"첫 글","views":0}],"limit":1,"page":1}

$ curl "localhost:18085/api/v1/posts?limit=500"
{"code":"INVALID_QUERY","message":"Key: 'ListQuery.Limit' Error:Field validation for 'Limit' failed on the 'max' tag"}  ← 400
```

글쓰기도 같아요. `views` 를 빼고 보내면 `required` 에 걸려요.

```bash
$ curl -X POST localhost:18085/api/v1/posts -H 'Authorization: Bearer t' -d '{"title":"셋째 글"}'
{"code":"INVALID_BODY","message":"Key: 'CreateReq.Views' Error:Field validation for 'Views' failed on the 'required' tag"}  ← 400
```

`Views` 를 `int` 가 아니라 `*int` 로 받은 데는 이유가 있어요. `int` 로 받으면 `{"views":0}` 도 400이 나요. 11장 2번에서 직접 비교해요.

`Bind`, `BindJSON` (Should가 없는 쪽)도 있어요. 이건 실패하면 gin이 400을 바로 써 버려서 응답 모양을 내가 못 정해요. 에러 응답을 통일하려면 늘 `ShouldBind` 계열을 써요.

## 07. 응답과 에러 응답 — `respond()` 대신 `c.JSON`

지금까지 본 401, 404, 400 응답이 전부 `{"code", "message"}` 모양이었죠. 03장에서 미리 만든 `fail` 덕분이에요. CI4 `ResponseTrait` 의 `respond()`, `failNotFound()`, `failValidationErrors()` 같은 건 gin에 없어요. 그래서 에러 응답 모양을 정해 두고 작은 함수 하나로 모아요. 핸들러마다 `gin.H{"error": ...}` 를 제각각 쓰면 금방 모양이 흩어져요.

에러가 service에서 핸들러로 넘어오는 길도 정해 둬요. 03장 `Service.Get` 과 04장 `Handler.Get` 에서 해당하는 줄만 모으면 이래요.

```
// service: HTTP를 몰라요. 무슨 일이 있었는지만 감싸서 돌려줘요
return Post{}, fmt.Errorf("post id=%d: %w", id, ErrNotFound)

// handler: 에러 종류를 보고 상태 코드를 골라요
if errors.Is(err, ErrNotFound) {
    fail(c, http.StatusNotFound, "POST_NOT_FOUND", "게시글이 없어요")
    return
}
```

- **service는 HTTP 상태 코드를 몰라요.** `%w` 로 감싸도 `errors.Is` 는 안쪽의 `ErrNotFound` 를 찾아요([03편](03-php-문법차이.md) 5장). 그래서 로그에는 "post id=99" 같은 자세한 내용이 남고, 응답은 404 하나로 정리돼요.
- **500일 때 `err.Error()` 를 그대로 내보내지 않아요.** SQL이나 내부 경로가 응답에 섞일 수 있어요. 자세한 내용은 로그에 남기고, 응답은 정해 둔 문구만 줘요.
- **핸들러가 많아지면 에러 미들웨어로 모아도 돼요.** 핸들러는 `c.Error(err)` 만 부르고, 미들웨어가 `c.Next()` 뒤에서 `c.Errors` 를 보고 응답을 써요. 스프링의 `@RestControllerAdvice` 와 비슷한 자리예요.

## 08. 서버 켜고 끄기 — `r.Run()` 대신 `http.Server`

[01편](01-실행방식.md)에서 본 것처럼 Go 서버는 실행 파일 하나가 직접 포트를 열어요. PHP-FPM이 워커를 정리해 주던 일을 이제 내 `main()` 이 해요. 03장 1단계에서 쓴 `r.Run(":18085")` 은 종료 신호를 받으면 처리 중인 요청까지 그냥 끊겨요. 그래서 게시글 API의 `main()` 은 `http.Server` 로 감싸서 `Shutdown` 을 불러요.

```go
func main() {
    gin.SetMode(gin.ReleaseMode)
    r := setupRouter(&Handler{svc: NewService()})

    srv := &http.Server{Addr: ":18085", Handler: r}
    go func() {
        if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
            log.Fatalf("listen: %v", err)
        }
    }()
    log.Println("listening on :18085")

    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit // 종료 신호가 올 때까지 기다려요
    log.Println("shutdown start")

    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()
    // 새 연결은 막고, 처리 중인 요청은 끝까지 기다려요
    if err := srv.Shutdown(ctx); err != nil {
        log.Println("shutdown:", err)
    }
    log.Println("shutdown done")
}
```

정말 처리 중인 요청을 기다리는지 보려고, 3초 걸리는 경로를 하나 붙였어요.

```go
r.GET("/slow", func(c *gin.Context) {
    time.Sleep(3 * time.Second)
    c.String(http.StatusOK, "done")
})
```

`/slow` 를 보내 놓고 0.5초 뒤에 서버에 SIGTERM 을 보냈어요. 그다음 새 요청도 하나 보냈어요. 아래는 서버 로그와 두 curl 결과예요.

```
2026/11/05 14:46:30 shutdown start
(새 요청)  curl: exit 7                               ← 새 연결은 거절돼요
2026/11/05 14:46:32 GET /slow -> 200 (3.001s)        ← 처리 중이던 요청은 끝까지 가요
(/slow 요청) done, exit 0
2026/11/05 14:46:33 shutdown done
```

`Shutdown` 은 처리 중인 요청이 다 끝난 걸 확인하고 나서 돌아와요. 10초(`WithTimeout`)가 지나도 안 끝나면 기다리지 않고 에러를 돌려줘요.

단, `Shutdown` 은 핸들러만 기다려요. 핸들러가 띄운 고루틴은 안 기다려요. 그런 작업이 있으면 `sync.WaitGroup` 으로 따로 기다려야 해요.

<details>
<summary>전체 코드 — 03~08장에서 붙인 조각을 모은 main.go</summary>

위 1단계처럼 모듈을 만들고 이 파일 하나를 두면 `go run .` 으로 그대로 돌아가요. 이 글의 curl 결과는 모두 이 코드로 낸 거예요.

```go
package main

import (
    "context"
    "errors"
    "fmt"
    "log"
    "net/http"
    "os"
    "os/signal"
    "sync"
    "syscall"
    "time"

    "github.com/gin-gonic/gin"
)

// ---------- 저장소: DB 대신 메모리에 둬요 (06편에서 MySQL로 바꿔요) ----------

type Post struct {
    ID    int64  `json:"id"`
    Title string `json:"title"`
    Views int    `json:"views"`
}

var ErrNotFound = errors.New("not found")

type Service struct {
    mu     sync.Mutex
    nextID int64
    posts  map[int64]Post
}

func NewService() *Service {
    return &Service{nextID: 2, posts: map[int64]Post{1: {ID: 1, Title: "첫 글", Views: 0}}}
}

func (s *Service) Get(ctx context.Context, id int64) (Post, error) {
    s.mu.Lock()
    defer s.mu.Unlock()
    p, ok := s.posts[id]
    if !ok {
        return Post{}, fmt.Errorf("post id=%d: %w", id, ErrNotFound)
    }
    return p, nil
}

func (s *Service) List(ctx context.Context, page, limit int) []Post {
    s.mu.Lock()
    defer s.mu.Unlock()
    out := []Post{}
    for id := int64(1); id < s.nextID; id++ {
        if p, ok := s.posts[id]; ok {
            out = append(out, p)
        }
    }
    start := (page - 1) * limit
    if start >= len(out) {
        return []Post{}
    }
    return out[start:min(start+limit, len(out))]
}

func (s *Service) Create(ctx context.Context, title string, views int) Post {
    s.mu.Lock()
    defer s.mu.Unlock()
    p := Post{ID: s.nextID, Title: title, Views: views}
    s.posts[p.ID] = p
    s.nextID++
    return p
}

// ---------- 에러 응답: 모양을 한 곳에서 정해요 ----------

type ErrorBody struct {
    Code    string `json:"code"`
    Message string `json:"message"`
}

func fail(c *gin.Context, status int, code, msg string) {
    c.AbortWithStatusJSON(status, ErrorBody{Code: code, Message: msg})
}

// ---------- 미들웨어 ----------

func Timing() gin.HandlerFunc {
    return func(c *gin.Context) {
        start := time.Now()
        c.Next()
        log.Printf("%s %s -> %d (%s)", c.Request.Method, c.Request.URL.Path,
            c.Writer.Status(), time.Since(start).Round(time.Millisecond))
    }
}

func Auth() gin.HandlerFunc {
    return func(c *gin.Context) {
        if c.GetHeader("Authorization") == "" {
            fail(c, http.StatusUnauthorized, "UNAUTHORIZED", "로그인이 필요해요")
            return
        }
        c.Next()
    }
}

// ---------- 핸들러 ----------

type Handler struct{ svc *Service }

type ListQuery struct {
    Page  int `form:"page,default=1"   binding:"min=1"`
    Limit int `form:"limit,default=20" binding:"min=1,max=100"`
}

type CreateReq struct {
    Title string `json:"title" binding:"required,max=100"`
    Views *int   `json:"views" binding:"required,min=0"`
}

func (h *Handler) List(c *gin.Context) {
    var q ListQuery
    if err := c.ShouldBindQuery(&q); err != nil {
        fail(c, http.StatusBadRequest, "INVALID_QUERY", err.Error())
        return
    }
    items := h.svc.List(c.Request.Context(), q.Page, q.Limit)
    c.JSON(http.StatusOK, gin.H{"items": items, "page": q.Page, "limit": q.Limit})
}

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

func (h *Handler) Create(c *gin.Context) {
    var req CreateReq
    if err := c.ShouldBindJSON(&req); err != nil {
        fail(c, http.StatusBadRequest, "INVALID_BODY", err.Error())
        return
    }
    p := h.svc.Create(c.Request.Context(), req.Title, *req.Views)
    c.JSON(http.StatusCreated, p)
}

// ---------- 라우터와 서버 ----------

func setupRouter(h *Handler) *gin.Engine {
    r := gin.New()
    r.Use(gin.Recovery(), Timing())

    posts := r.Group("/api/v1/posts")
    posts.GET("", h.List)
    posts.GET("/:id", h.Get)

    w := posts.Group("", Auth())
    w.POST("", h.Create)

    r.GET("/slow", func(c *gin.Context) {
        time.Sleep(3 * time.Second)
        c.String(http.StatusOK, "done")
    })
    return r
}

func main() {
    gin.SetMode(gin.ReleaseMode)
    r := setupRouter(&Handler{svc: NewService()})

    srv := &http.Server{Addr: ":18085", Handler: r}
    go func() {
        if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
            log.Fatalf("listen: %v", err)
        }
    }()
    log.Println("listening on :18085")

    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit
    log.Println("shutdown start")

    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()
    if err := srv.Shutdown(ctx); err != nil {
        log.Println("shutdown:", err)
    }
    log.Println("shutdown done")
}
```

</details>

## 09. 폴더 나누기와 context

지금은 `main.go` 한 파일이지만, 실제 서비스는 이렇게 나눠요. 전체 코드의 `// ----------` 구분선이 거의 그대로 파일이 돼요.

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

## 10. CodeIgniter, 스프링과 한눈에 비교

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

## 11. 조심할 것

### 1. `c.Abort()` 는 함수를 끝내지 않아요

**상황:** `id` 가 없으면 400을 내려고 Abort를 불렀는데, 바로 뒤에 `return` 을 빼먹었어요.

**해 본 것:** 아래 핸들러에 `id` 없이 요청을 보냈어요.

```
if c.Query("id") == "" {
    c.AbortWithStatusJSON(400, gin.H{"error": "id required"})
    // return 빠짐
}
c.JSON(200, gin.H{"ok": true})

// 결과: status=400 body={"error":"id required"}{"ok":true}
```

**결과:** 상태 코드는 400인데 본문에는 JSON 두 개가 이어 붙었어요. 클라이언트는 이 본문을 JSON으로 못 읽어요.

**왜:** Abort는 "뒤에 남은 핸들러를 부르지 마"라는 표시만 남겨요. 지금 함수는 계속 돌아서 `c.JSON(200, ...)` 까지 실행돼요. 상태 코드는 처음 쓴 400이 남고, 본문만 덧붙어요. 미들웨어에서 빼먹으면 뒤의 핸들러는 안 불려도, Abort 다음 줄(로그, DB 조회 등)은 실행돼요.

### 2. `binding:"required"` 는 0을 "값 없음"으로 봐요

**상황:** 06장 `CreateReq` 의 `Views` 를 처음에는 `int` 로 받았어요. 조회수 0으로 글을 만들려고 하니 400이 났어요.

**해 본 것:** `Views` 의 타입과 보내는 본문을 바꿔 가며 글쓰기를 보냈어요.

```
Views int  + required, {"views":0}  → 400 failed on the 'required' tag
Views *int + required, {"views":0}  → 201 {"title":"a","views":0}
Views *int + required, {}           → 400 failed on the 'required' tag
```

**왜:** `int` 는 값을 안 보내도 0이 들어가요([03편](03-php-문법차이.md)의 제로 값). 그래서 `required` 는 "안 보냄"과 "0을 보냄"을 구분하지 못하고 둘 다 막아요. `*int` 로 받으면 안 보냈을 때 `nil`, 0을 보냈을 때 0을 가리키는 포인터라서 구분돼요. `false`, `""` 도 같아요.

### 3. `gin.Context` 를 고루틴에 그대로 넘기지 않아요

**상황:** 응답을 먼저 주고 남은 일(알림 보내기 같은 것)을 고루틴으로 돌리고 싶어요.

**해 본 것:** `/a` 핸들러에서 고루틴을 띄우고, 50ms 뒤에 원래 `c` 와 복사본 `cCp` 의 경로를 찍었어요. `/a` 응답 직후 `/b` 요청을 보냈어요.

```go
r.GET("/a", func(c *gin.Context) {
    cCp := c.Copy()
    go func() {
        time.Sleep(50 * time.Millisecond)
        log.Println(c.Request.URL.Path, cCp.Request.URL.Path)
    }()
    c.Status(202)
})

// 결과: original c sees "/b", c.Copy sees "/a"   (go test -race 는 DATA RACE로 실패)
```

**결과:** 원래 `c` 는 `/a` 를 처리하던 객체인데 `/b` 를 가리켰어요. 복사본은 `/a` 그대로였어요.

**왜:** gin은 성능 때문에 `gin.Context` 를 `sync.Pool` 로 재활용해요. `/a` 응답이 끝나자 같은 객체가 `/b` 요청에 쓰였어요. 고루틴에 넘길 땐 `c.Copy()` 로 복사해요. 복사본도 `c.Request.Context()` 는 요청이 끝나면 취소돼요. 응답 뒤에도 돌아야 하는 작업은 필요한 값만 꺼내서 새 context로 시작해요.

### 4. `gin.Default()` 에는 Logger와 Recovery가 들어 있어요

03장 1단계 로그의 `(3 handlers)` 가 이거예요. 내 핸들러는 하나인데 셋으로 나온 건 `gin.Default()` 가 Logger, Recovery 두 개를 붙였기 때문이에요. 게시글 API는 `Timing` 을 따로 붙여서 `gin.New()` 로 시작했어요. `gin.Default()` 로 시작하면 로그가 두 번 찍혀요.

대신 Recovery는 꼭 붙여요. 빼먹으면 panic이 난 요청은 응답 없이 연결이 끊겨요(curl에는 EOF). 서버 전체가 죽지는 않아요.

### 5. 운영에서는 release 모드로 띄워요

03장 1단계 로그의 `Running in "debug" mode. Switch to "release" mode in production.` 경고가 이거예요. debug 모드는 라우트 목록과 경고를 찍어요. `GIN_MODE=release` 환경 변수나 `gin.SetMode(gin.ReleaseMode)` 로 바꿔요. 게시글 API의 `main()` 첫 줄이 이거예요.

## 12. 스스로 확인해 보기

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

## 13. 참고한 글

- [미들웨어](https://gin-gonic.com/ko-kr/docs/middleware/) — gin 공식 문서(한국어). `c.Next()` 앞뒤로 나뉘는 양파 구조, 미들웨어를 붙이는 범위
- [미들웨어 내 고루틴](https://gin-gonic.com/ko-kr/docs/middleware/goroutines-inside-a-middleware/) — gin 공식 문서(한국어). `sync.Pool` 재활용과 `c.Copy()`
- [Graceful Restart or Stop](https://gin-gonic.com/ko-kr/docs/server-config/graceful-restart-or-stop/) — gin 공식 문서(한국어). `http.Server.Shutdown` 예제
- [Gin](https://velog.io/@connor/Gin) — velog. 라우팅, 바인딩, 렌더링, 미들웨어, 서버 설정을 예제로 한 번에 훑기
- [\[Golang\] ShouldBindJson 와 BindJSON](https://velog.io/@imsooyeon/Golang-ShouldBindJson-%EC%99%80-BindJSON) — velog. 스프링 `@RequestBody` 와 비교
- [\[go/gin\] 요청 Validation에 대해 알아보자](https://velog.io/@beardfriend/gogin-%EC%9A%94%EC%B2%AD-Validation%EC%97%90-%EB%8C%80%ED%95%B4-%EC%95%8C%EC%95%84%EB%B3%B4%EC%9E%90) — velog. `required`, `min`/`max`, `oneof`, 커스텀 검사 등록
- [Graceful shutdown?](https://velog.io/@smoothbear/graceful-shutdown) — velog. gin + `http.Server` 로 SIGINT/SIGTERM 처리
