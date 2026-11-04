---
title: "http의 정의와 https 차이"
date: 2022-01-14
tags: ["네트워크"]
source: https://app.notion.com/p/99a59a6227ff4dd8bd8ec09d0b3a3ea6
---

# http의 정의와 https 차이

## http란?

: HTTP(Hypertext Transfer Protocol) 즉, 통신 프로토콜이다.

### 특징 및 장점

1. 무상태(stateless) 프로토콜이다.
   : 데이터를 주고 받기 위한 각각의 데이터 요청이 서로 독립적으로 관리가 된다는 뜻

   → 이전 데이터 요청과 이후 데이터 요청은 관련이 없다.

2. 서버는 세션과 같은 별도의 추가 정보를 관리하지 않아도 된다.
3. 다수의 요청 처리 및 서버의 부하를 줄일 수 있다.
4. TCP/IP 통신 위에서 동작하고 기본 포트는 80번이다.

이외에도 http 메소드등이 있는데

> ⚠️ 노션에서만 보이는 블록(alias)이라 옮기지 못했어요. [노션 원본](https://app.notion.com/p/99a59a6227ff4dd8bd8ec09d0b3a3ea6#06d0595feb7a44bd98ccb5dc9b5b8e8d)

에 정리가 되어있다.

## http와 https의 차이

: https는 http에 **데이터 암호화가 추가된 프로토콜**이다.

즉, http보다 https는 보안성이 좋고 암호화/복호화 과정이 필요하기 때문에 http보다 속도가 느리다.

그리고 https는 인증서를 발급하고 유지하기 위한 추가 비용이 발생한다.

### ⇒ 개인정보와 같은 민감한 데이터를 주고 받아야 한다면 HTTPS를 이용해야 하지만, 단순한 정보 조회 등만을 처리하고 있다면 HTTP를 사용하면 된다.

### 특징

1. 포트 번호가 443번이다.
2. 네트워크 상에서 중간에 제 3자가 정보를 볼 수 없도록 공개키 암호화를 지원한다.
   1. 공개키 : 모두에게 공개하는 키
   2. 개인키 : 나만 가지고 알고 있어야 하는 키

Reperence: [https://mangkyu.tistory.com/98](https://mangkyu.tistory.com/98)
