---
title: "NULL 관련 함수"
date: 2022-01-23
tags: ["ORACLE"]
source: https://app.notion.com/p/6bd1eb006b0443edb1cc29ca36951149
---

# NULL 관련 함수

### 기본적으로 NULL에 무슨 값을 더해도 NULL이 나오게 되어있다.

즉, SELECT NULL+3 FROM DUAL; 은 NULL이 출력됨

그렇기때문에 NULL을 대체하는 값을 대입해줘야함

## NVL(NULL, 대체값) 함수 → NULL 대체 함수

- SELECT NVL(AGE, 0) FROM MEMBERS;

## NVL에서 조건을 하나 더 추가한 NVL2(입력값, NOTNULL대체값, NULL대체값) 함수

- SELECT NVL2(AGE,AGE/100,0) FROM MEMBERS;

  - NULL이 아니면 연산값을 NULL이면 0을 대입해줌

## 두 값이 같은 경우 NULL 그렇지 않은 경우 첫번째 값 반환

- SELECT NULLIF(AGE,19) FROM MEMBERS;
  - 19살이면 NULL 아니면 AGE

## 조건에 따른 값 선택하기 DECODE(기준값, 비교값, 출력값, 비교값, 출력값)

- SELECT DECODE(GENDER,’남성’, 1, 2) FROM MEMBERS;
  - 남성일 경우에 1을 아니면 2를 반환
- SELECT DECODE(SUBSTR(PHONE,1,3), ‘011’, ‘SK’, ‘016’, ‘KT’, ‘기타’) FROM MEMBERS;
  - 011이면 SK를 016이면 KT를 둘다 아니면 기타를 반환해준다.
