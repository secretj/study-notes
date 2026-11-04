# UNION

> 작성: 2022-01-25 · 태그: ORACLE · [노션 원본](https://app.notion.com/p/0fc0bc33ad604102ac68c40b98a17d8b)

### UNION (중복 제거)

- 만약 여러 개의 테이블이 있는데 통합 검색을 하고 싶을 때, UNION으로 합쳐서 검색하면 된다.
  ```sql
  SELECT ID, NAME FROM MEMBER
  UNION
  SELECT WRITER, TITLE FROM NOTICE;
  // 쿼리와 쿼리 사이에 UNION 붙여주면 됨(단, 중복은 제거된다.)
  
  ```

### UNION ALL(중복 제거 안함 그냥 그대로 이어 붙인다.)

- 중복 제거 안하고 있는 그대로 이어 붙인다.

```sql
SELECT ID,NAME FROM MEMBER
UNION ALL
SELECT WRITER, TITLE FROM NOTICE;
```

### MINUS

- 공통된 부분을 뺀다.

```sql
SELECT ID,NAME FROM MEMBER
MINUS
SELECT WRITER, TITLE FROM NOTICE;
```

### INTERSECT

- 공통된 부분만 남긴다.

```sql
SELECT ID,NAME FROM MEMBER
INTERSECT
SELECT WRITER, TITLE FROM NOTICE;
```
