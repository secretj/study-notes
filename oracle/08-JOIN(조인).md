---
title: "JOIN(조인)"
date: 2022-01-23
tags: ["ORACLE"]
source: https://app.notion.com/p/e5fc666736814c3bae14f0dcfc38d342
---

# JOIN(조인)

### 테이블을 합치는 기법

SELECT \* FROM MEMBER;

SELECT \* FROM NOTICE;

두 테이블을 조인해보자

- SELECT \* FROM MEMBER INNER JOIN NOTICE ON [MEMBER.ID](http://MEMBER.ID) =NOTICE.WRITER\_ID;

⇒ 기준 테이블 JOIN 합칠 테이블 ON 조인할 조건

![](images/f3d60368-d10c-450c-bffc-2c5ca2a90bdb.png)

- 관계가 **있는** 레코드는 **INNER**
- 관계가 **없는** 레코드는 **OUTER**가 된다.

![](images/191625b3-d7e9-4da4-be9a-dd0a6aab317c.png)

여기선 글을 쓴 회원은 INNER

글을 쓰지 않은 회원은 OUTER가 된다.

## INNER JOIN

- SELECT \* FROM MEMBERS M INNER JOIN NOTICE N ON M.Member\_ID=N.Writer;
  - MEMBERS 테이블과 NOTICE 테이블의 조건에 맞는 부분만 보여주겠다는 것

## OUTER JOIN

- LEFT/RIGHT/FULL OUTER JOIN 이렇게 세 종류가 있음(OUTER 생략 가능)
  - LEFT는 먼저 선언한 테이블의 키 값에 맞지 않는 부분도 보여주겠다는 것

  ![](images/d636fa36-4051-40bc-bdcf-6ce607076991.png)

  - RIGHT는 나중에 선언한 테이블의 키 값에 맞지 않는 부분도 보여주겠다는 것
  - FULL은 전부 보여주겠다는 것

  ```sql
  //오라클에서 JOIN 문법은 ANCI와 다르다.
  SELECT * FROM MEMBER M, NOTICE N
  WHERE M.ID=N.WRITER(+)
  
  //이런식으로 조인할 테이블을 나열하고 WHERE에서 조건을 건다.
  // (+)가 있는 부분은 OUTER 조인할 부분이다.
  ```

  

  
- 다음 테이블을 RIGHT OUTER JOIN을 하면 총 레코드 개수는 몇 개인가?

![](images/bbdf9849-7ecd-47f4-8630-64c543aa80db.png)

5개

- 다음 테이블을 FULL OUTER JOIN을 하면 총 레코드 개수는 몇 개인가?

![](images/5ad0ccf7-5a6b-45c6-8713-86edafc01870.png)

8개

## SELF JOIN

: 같은 테이블끼리 조인

- 데이터가 서로 포함 관계를 가지는 경우 : 담당, 구성, 연락

![](images/e8e1f0a0-8ae3-4993-908a-40198975c1aa.png)

- 참조 컬럼이 필요함

![](images/767da775-69d7-46e8-9be1-ecac5ec7bdca.png)
