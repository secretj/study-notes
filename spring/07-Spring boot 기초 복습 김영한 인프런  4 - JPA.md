---
title: "Spring boot 기초 복습 김영한 인프런  4 - JPA"
date: 2023-07-03
tags: ["Spring"]
source: https://app.notion.com/p/0ad96f7fecc14d928790ce952881921e
---

# Spring boot 기초 복습 김영한 인프런  4 - JPA

## JPA

JPA는 ORM이다 - 객체(Object)와 관계형 데이터베이스(RDBMS)를 맵핑(Mapping) 시킨다.<br>JPA의 가장 큰 장점은 DB를 중간에 바꾸더라도 별도의 쿼리 변경없이 사용할 수 있다는 점이다.

- DB에 값을 넣으면 SEQ처럼 자동으로 값을 넣어주는 방식을 INDENDITY라고 한다.
- JPA는 모든 데이터의 변경이 Transactional안에서 실행되어야한다. <br>그래서 사용할 서비스계층에 @Transactional을 붙여줌

### 스프링 데이터 JPA

SpringDataJpaMemberRepository .java

```java
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

//인터페이스에 JpaRepository를 상속받으면 구현체를 JPA가 스스로 만들어내고 BEAN에 등록해둔다.
//-> 그래서 MemberRepository를 따로 등록하지않아도 SpringConfig에서 꺼내쓰는걸 볼 수 있음
public interface SpringDataJpaMemberRepository extends JpaRepository<Member, Long>, MemberRepository {

    //save나 findById같이 우리가 만들었던 메소드들을 전부 JpaRepository에서 공통으로 제공하기때문에
    //findByName만 구성해놓은 모습(그 외 페이징기능등 다양한 기능을 지원한다.)
    @Override
    Optional<Member> findByName(String name);
}
```

SpringConfig.java

```java
@Configuration
public class SpringConfig {

    private final MemberRepository memberRepository;

    @Autowired
    public SpringConfig(MemberRepository memberRepository) {
        this.memberRepository = memberRepository;
    }

		@Bean
    public MemberService memberService() {
        return new MemberService(memberRepository);
    }
}
```
