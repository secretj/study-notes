---
title: "stack, heap그리고 static"
date: 2022-02-24
tags: ["JAVA"]
source: https://app.notion.com/p/2a018103e564465ca62b3acdabb22957
---

# stack, heap그리고 static

### 데이터 영역

- 전역 변수와 static변수가 할당되는 메모리 영역이다.
- 프로그램의 시작과 동시에 할당되고 프로그램이 종료되어야 메모리에서 사라지는 영역이다.

→ 프로그램이 시작하기 전부터 끝까지 존재하는 메모리 영역 → 부하가 제일 크다. (계속 올려놔야하니까)

### 스택(Stack 영역)

- 함수 호출 시 생성되는 지역 변수와 매개 변수가 저장되는 영역
- 함수 호출이 완료되면 사라짐

### 힙(Heap) 영역

- 동적으로 할당된 변수

```c
#include <stdio.h>

void foo(int a);

int val = 10;                      // 'val' 는 데이터 영역
char string[] = "Hello World";    // 'string' 은 데이터 영역
																	// 전역변수기 때문 !

int main() {
    int i = 100;    // 'i'는 stack 영역
    foo(i);
    return 0;
}

void foo(int a) {   // 'a' in stack area
    int* ptr = (int*) malloc(sizeof(int)*a);   // 'ptr'은 힙메모리 영역
}

```

출처: https://greatzzo.tistory.com/57 \[What a Great World!!\]
