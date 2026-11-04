# public static void main(String[] args)

> 작성: 2022-01-18 · 태그: JAVA · [노션 원본](https://app.notion.com/p/9eb8fd27a6be4952aa90d09df0e3da4a)

### 서문

java에서 프로젝트를 생성한 첫 클래스에는 항상 public static void main(String\[\] args)가 쓰여져있다.

메인 메소드라고 부르는 이것은 사실 자바를 처음 배울 때, 배웠던 것인데 직접 입력해본지 오래되서인지 언제부턴가 잊고 지내다가 새로운 프로젝트를 하드 코딩으로 시작하려고 하다가 왜 있었는 지 잊어서 다시 정리해보려고한다.

### public

어디서든 접근이 가능한 접근 제한자이다.

### static

정적 함수라고 한다.

자바에서 메모리 할당 방법은 두가지가 있는데 하나는 static 영역, 두번째는 heap 메모리 영역에 저장하는 것이다.

heap메모리에 저장된 것 , 즉 new해서 할당해준 메모리는 Garbage Collector에 의해 정리가 된다.

하지만 메인 함수가 Garbage Collector에 의해 제거가 된다면, 프로그램이 제대로 돌 수가 없기때문에 정리되지 않는 static 영역에 할당하는 것이다.

### void

이건 함수가 끝날 때 return값이 없다는 것을 뜻한다.

main 메소드가 끝난다는 것은 곧 프로그램 종료를 의미하는데, return값이 있으면 이상하죠?

### String\[\]

String형태의 배열을 선언한다는 뜻

### args

그냥 변수이름이다. 다른 걸로 써도 된다.
