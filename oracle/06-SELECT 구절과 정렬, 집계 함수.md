# SELECT 구절과 정렬, 집계 함수

> 작성: 2022-01-23 · 태그: ORACLE · [노션 원본](https://app.notion.com/p/084817bec7af41c0b18e257bfddc10d4)

### SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY 의 순으로 작성

### FROM

: 격자형 구조를 만들어내는 공간

### WHERE

: 필터링 공간

### GROUP BY

: 집계 함수 공간(COUNT, AVG, MAX, MIN 등 )

### HAVING

: 집계된 내역을 필터링(집계 내역은 WHERE에서 사용 불가)

예) COUNT(ID)≥2

## ORDER BY

: 정렬

- ASC
  - 정방향
    - SELECT \* FROM NOTICE ORDER BY HIT;
- DESC
  - 역방향
    - SELECT \* FROM NOTICE ORDER BY HIT DESC
- 예) 회원 중에서 ‘박’씨 성을 가진 회원을 조회하시오.(단, 나이를 오름차순으로 정렬)
  - SELECT \* FROM MEMBERS WHERE NAME LIKE ‘박%’ ORDER BY AGE ASC;
- 중첩해서 사용하면 정렬의 조건을 여러개 걸 수 있다.
  - SELECT \* FROM NOTICE WHERE HIT>3 ORDER BY HIT DESC, REGDATE DESC;

  

## GROUP BY

: 집계 함수

### COUNT

- SELECT COUNT(ID) FROM NOTICE;

  - 해당 컬럼의 로우 수
- SELECT SUM(HIT) FROM NOTICE;

  - 해당 컬럼의 전체 합
- SELECT AVG(HIT) FROM NOTICE;

⇒ 근데 작성자 별로 몇번 글을 썼는 지 궁금하다.

→ GROUP BY 사용 - SELECT WRITER\_ID, COUNT(ID) FROM NOTICE GRUOP BY WRITER\_ID;

예) SELECT WRITER\_ID, COUNT(ID) COUNT FROM NOTICE GROUP BY WRITER\_ID ORDER BY COUNT DESC;

- 실행 순서

1. FROM절
2. CONNECT BY 절
3. WHERE 절
4. GROUP BY 절
5. HAVING 절
6. SELECT 절
7. ORDER BY 절

고로 별칭은 정렬할 때만 사용 가능하다.

## HAVING 절

: 집계 함수의 조건을 걸기 위해 사용

### 왜 WHERE절을 안쓰고?

: WHERE절은 GROUP BY 이전에 실행되기 때문에 즉, 집계가 되기 전에 이미 끝남

그래서 사용할 수 없음. 그래서 HAVING에서 조건을 걸어준다.

예) SELECT WRITER\_ID, COUNT(ID) COUNT FROM NOTICE GROUP BY WRITER\_ID HAVING COUNT(ID) ≤2 ORDER BY COUNT ASC;
