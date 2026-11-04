---
title: "VIEW"
date: 2022-01-25
tags: ["ORACLE"]
source: https://app.notion.com/p/729ac1a6b6f443308c3f57dea3942187
---

# VIEW

### VIEW가 생기게 된 이유?

물리적인 데이터구조인 TABLE은

![](images/5d8f7685-169a-4174-88a5-4a81afb8753f.png)

이 모습처럼 정규화되어 분리되어 있다.

근데 우리가 실제로 사용할 때는 이 테이블들을 합쳐서 사용하게 되는데

업무적으로 자주 쓰이는 쿼리를 매번 합치기 불편하기 때문에

합쳐놓은 쿼리문을 VIEW로 정의해서 마치 테이블처럼 가져다 쓸 수 있게 되었다.

![](images/bc592eeb-e6ad-4d44-9000-9a6ff3c353ee.png)

![](images/e0e27274-9546-4992-97a3-6e766b259cb0.png)

위 사진처럼 세 테이블을 모두 합쳐 사용하려고 두 번의 JOIN을 한 것을 볼 수 있다.

그래서 이것을 뷰로 만들게 되면

![](images/4ea3d872-8e61-4d20-824e-efc4e776dc9e.png)

이처럼 한번 정의하고 쉽게 가져가서 쓸 수 있는 것을 볼 수 있다.

![](images/7bb293ff-7a80-4909-b746-8fcedd8de46d.png)

### VIEW 생성법

```sql
CREATE VIEW ‘생성할 VIEW명’
AS
(
쿼리
)
```

![](images/42ea50f5-f5b1-40a4-909b-911f78cfd55b.png)

**Oracle SQL Developer 대시보드에 뷰에서 생성된 뷰를 확인할 수 있다.**

![](images/7e8c6e0c-72d6-4bec-85a7-33b46c6771f3.png)

**⇒ 이렇게 생성한 뷰 사용 가능한 것을 확인 가능 !**
