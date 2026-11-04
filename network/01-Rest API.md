---
title: "Rest API"
date: 2022-01-04
tags: ["네트워크"]
source: https://app.notion.com/p/72c504468353414bbbe7224ef11d0f24
---

# Rest API

## REST 란?

**Representational State Transfer**의 약자

- 자원을 이름으로 구분하여 해당 자원의 상태(정보)를 주고 받는 모든 것
  - 자원 : 문서, 그림, 데이터, 해당 소프트웨어 자체등
  - 자원의 표현 : 그 자원을 표현하기 위한 이름
    - : 학교가 자원이면, ‘school’을 자원의 표현으로 정함
- 상태 전달
  - 데이터가 요청되는 시점에 자원의 상태를 전달
  - JSON 이나 XML로 데이터를 주고 받는 것이 일반적
- REST는 HTTP 프로토콜을 그대로 활용하기 때문에 웹의 장점을 최대한 활용할 수 있음
- REST는 네트워크 상에서 Client와 Server 사이의 통신 방식 중의 하나
  

### REST의 개념

HTTP URI(Uniform Resource Identifier)를 통해 **자원(Resource)을 명시**하고, **HTTP Method(POST, GET, PUT, DELETE)**를 통해 해당 자원에 대한 **CRUD Operation**을 적용하는 것을 의미한다.

**CRUD Operation**

- Create : 생성(POST)
- Read : 조회(GET)
- Update : 수정(PUT)
- Delete : 삭제(DELETE)
- HEAD: header 정보 조회(HEAD)

즉, REST는 자원 기반의 구조(ROA, Resource Oriented Architecture) 설계의 중심에 자원(Resource)이 있고 HTTP Method를 통해 자원을 처리하도록 설계된 구조를 의미한다.<br>웹 사이트의 이미지, 텍스트, DB 내용 등의 모든 자원에 고유한 ID인 HTTP URI를 부여한다.

⇒ 기존에 내가 쓰던 방식은 localhost.member?a=3&ab=5 이렇게 생겼는데

REST API로 만든 URI는 보통 명사로 구성되서 localhost.member/a/3/ab/5 이런식으로 생김

### REST 특징

1. **Server-Client(서버-클라이언트 구조)**

- 자원이 있는 쪽이 Server, 자원을 요청하는 쪽이 Client가 된다.
  - REST Server : API를 제공하고 비지니스 로직 처리 및 저장
  - Client : 사용자 인증이나 context(세션, 로그인 정보)등을 직접 관리
- 서로 간 의존성이 줄어든다.

2. **무상태(Stateless)**

- HTTP 프로토콜은 무상태 프로토콜이므로 REST도 무상태성을 갖는다.
- Client의 context를 서버에 저장하지 않는다.
  - 즉, 세션과 쿠키와 같은 context 정보를 신경쓰지 않아도 되므로 구현이 단순해진다.
- 서버는 각각의 요청을 완전히 별개의 것으로 인식하고 처리한다.
  - 각 API서버는 클라이언트의 요청만을 단순 처리
  - 즉, 이전 요청이 다음 요청의 처리에 연관되지 않는다.
  - 물론 이전 요청이 DB를 수정하여 DB에 의해 바뀌는 것은 허용
  - 서버의 처리 방식에 일관성을 부여하고 부담이 줄어들며, 서비스의 자유도가 높아짐

3. **캐시 처리 가능**
   - 웹 표준 HTTP 프로토콜을 그대로 사용하기 때문에 캐싱 기능 적용 가능
   - 그렇기 때문에 응답시간이 빨라지고 REST Server 트랜잭션이 발생하지 않음 → 빨라지고 서버의 자원 이용률 증가
4. **계층화**
   - REST Server는 다중 계층으로 구성됨
     - 구조가 유연하고 보안성과 확장성이 좋아짐
5. **인터페이스 일관성**  
   - URI로 지정한 자원에 조작을 통일되고 한정적인 인터페이스로 수행
   - HTTP 표준 프로토콜에 따르는 모든 플랫폼에서 사용 가능

  

## 그러면 REST API는 뭘까?

- API : 데이터와 기능의 집합을 제공하여 컴퓨터 프로그램간 상호작용을 촉진하며. 서로 정보를 교환 가능 하도록 하는 것 !
- REST API ?

  : REST 기반으로 서비스 API 구현한 것!!

### REST API 특징

- **HTTP 표준을 기반**으로 하기 때문에 HTTP를 지원하는 프로그램 언어로 클라이언트, 서버 구현 가능
- REST 기반으로 시스템을 분산해 확장성과 재사용성을 높여 유지보수 및 운용을 편리하게 함

### REST 설계 규칙

- URI는 정보의 자원을 표현해야 한다.
  - 자원은 동사보다 명사, 대문자보다는 소문자
  - 자원은 도큐먼트는 단수 명사, 컬렉션 이름은 복수명사, 스토어 이름은 복수 명사 사용
    - Ex) GET /Member/1 -> GET /members/1
- 자원에 행위는 HTTP Method로 표현한다.
- 슬래시(/)는 **계층 관계**를 나타내는데 사용한다.
- URI 마지막은 슬래시(/)를 포함하지 않는다. (끝에 슬래시 넣지 말라는 뜻)
- 밑줄은 URI에 사용하지 않는다.
- 파일 확장자는 URI에 포함하지 않는다. (Accept header를 사용)
  

  

  

  

  

References : [https://gmlwjd9405.github.io/2018/09/21/rest-and-restful.html](https://gmlwjd9405.github.io/2018/09/21/rest-and-restful.html)
