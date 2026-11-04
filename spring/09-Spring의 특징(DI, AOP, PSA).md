---
title: "Spring의 특징(DI, AOP, PSA)"
date: 2023-07-03
tags: ["Spring"]
source: https://app.notion.com/p/0673c2c580484c1d8ed43e5a5eb20b74
---

# Spring의 특징(DI, AOP, PSA)

### Spring의 특징을 따지면 크게 세가지로 분류할 수 있다.

## 1.IOC(제어의 역전), DI (의존성 주입)

:  객체간의 의존성을 자신이 아닌 외부에서 주입하는 개념

### 그전에 의존성은 뭔데 ?

```java
public class MessageBeanKr{
		public void sayHello(String name){
			System.out.println("안녕하세요,"+name+"!");
		}
}

public class MessageBeanEn{
		public void sayHello(String name){
			System.out.println("Hello,"+name+"!");
		}
}
// MessageBeanEn이란 클래스에 sayHello라는 메소드를 정의하고

public class HelloApp{
	public static void main(String[] args){
			MessageBeanEn bean = new MessageBeanEn();
			bean.sayHello("Spring");
	}
}
/* 자 HelloApp이라는 클래스에서 위의 클래스안의 메소드를 호출하고 spring을 넣으면
결과값이 */
실행 결과 : Hello, Spring!
// 당연히 MessageBeanKr을 호출하면 안녕, Spring! 이 나온다
```

자 위처럼 구현을 하게 되면

메인의 MessageBeanEn을 MessgeBeanKr로 변경해줘야하고

**이런 경우에 HelloApp이 MessageBeanEn(Kr)에 의존성을 가지고 있다고 한다**.

→ 나는  해당 클래스의 변경을 위해서 함께 객체를 변경시켜야만 하면으로 이해했음

메인 기능을 변경하기 위해서 MessageBean도 함께 변경을 해줘야 하기 때문이다.

이러한 의존성을 해결하기 위해서는 **외부에서 객체의 인스턴스를 생성받아야** 하는데

이 방법에는 세가지가 있다.

1. 생성자를 이용한 의존성 주입
2. setter메소드를 이용한 의존성 주입
3. 초기화 인터페이스를 이용한 의존성 주입

그중 스프링이 지지하는 방식은 setter를 이용한 의존성 주입이다.

이것을 줄이기 위해서 인터페이스를 생성해보자

```java
public interface MessageBean{
			public void sayHello(String name);
}
// sayHello 추상메서드가 들어간 인터페이스를 만들고

public class MessageBeanKr implements MessageBean{
	public void sayHello(String name){
		System.out.println("안녕하세요,"+name+"!");
	}
}

public class MessageBeanEn implements MessageBean{
	public void sayHello(String name){
		System.out.println("Hello,"+name+"!");
	}
}

public class HelloApp{
	public static void main(String[] args){
		MessageBean bean  = new MessageBeanKr();
		bean.sayHello("Spring");  // 대입문을 En으로 바꾸면 영어로 출력됨
	}
}
```

메인에서의 소스코드 변형은 살짝(너무 살짝 아니냐?)  줄어든 것을 볼 수 있지만

이 역시 변형이 일어난다.

이러면 뭐라고? HelloApp이 MessageBeanKr에 의존 중이라고 \~

아래는 설정 파일을 추가했다. MessageBean에 주입할 객체에 대한 설정 정보가 담겨있다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmls ~~~생략 xml 맨위에 있는거>

<bean id="messageBean" class="sample1.MessageBeanKr"/>
<!--sample1은 패키지명이다. Kr을 En으로 변경 시 영문이 출력된다. 여기선 한글로 설정했다는 것 -->

```

```java
public class HelloApp{
	public static void main(String[] args){
		BeanFactory factory = new XmlBeanFactory(new FileSystemResource("resources/beans.xml"));

	/*bean이 사용하는 클래스 이름을 코드에 직접 쓰지 않은걸 볼 수 있다
	-> 이럼 뭐라고? 의존하지 않는다고*/
		MessageBean bean = factory.getBean("MessageBean", MessageBean.class);
		bean.sayHello("Spring");

출력 결과 : 안녕하세요, Spring !
```

<br>

결론으로는 스프링에서 DI(의존성 주입)은 객체의 실체를 외부 환경설정(spring config xml, Bean 객체, 어노테이션등)으로 컨트롤 할 수 있도록 하는 것이다.

**왜? 모듈 간의 결합도를 낮춰서 유연한 변경을 가능하도록 하기 위하여 !**

## 2.AOP

[링크](02-AOP의%20이해.md)

절차지향프로그래밍에서 편의성을 위해 개선된 관점 지향 프로그래밍이라고 하는데

한번에 처리해도 되는 공통적인 기능을 하나하나 다 구현하려니까 속터져서 만든 기능적인 면에서 접근해서 한번에 똑딱 묶어서 처리하는거라고 이해함

(예를 들면 뭐 트랜젝션이라던지 예외 처리라던지 로깅이라던지 \~ )

## 3. PSA(Portable Service Abstraction)

경량화임
