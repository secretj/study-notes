---
title: "Factory와 Mapper"
date: 2024-01-31
tags: ["JAVA", "Pattern"]
source: https://app.notion.com/p/03fc9d1d4fab4ff097e4300a496e4dd2
---

# Factory와 Mapper

목차

## 🔆 Factory Pattern

: 하나의 공장에서 여러 제품을 만들어내듯이, <br> 공장 역할을 하는 **객체에서 조건에 따라 분기를 해서 필요한 객체를 만들어내는 방식**이 바로 **팩토리 패턴**이다.<br>

### ⁕ 유의 사항

- 공통점이 어느정도 있는 객체를 생성하는 팩토리를 만들어야한다.<br>→ 자동차 공장에서 옷을 만들 수는 없다.
- 비슷한 큰 틀을 가진 객체를 분기에 따라 세부 내용을 바꿔 다르게 생성해서 사용할 때 사용하기 좋다.

### ⁕ Mecca-2 개발 환경에 맞는 예시

> 우리가 Factory와 Mapper를 쓰려고 하는 이유는 <br>1. 연관된 객체의 생성을 담당하는 모듈 - Factory (복잡성이 떨어지면 Factory에서 해도 좋다)<br>2. 그 연관된 객체를 만들기 위한 데이터를 가공하는 모듈 - Mapper<br>어디에서 그 책임을 가져갈 것인가에 대한 고민이었는데, 조사를 해본 결과 Factory에서 모두 해결해도 되지만<br>Mapping에 대한 책임을 Mapper에서 하면 좋다는 결론에 도달하여 예시 코드를 작성해본다.

```php
class BoardMapper
{
    public static function createNoticeBoard($requestData)
    {
        $data = [
            'title' => $requestData['title'],
            'content' => $requestData['content'],
            'author' => $requestData['author'],
            'notice_type' => $requestData['notice_type'],
        ];

        $noticeModel = new NoticeBoardModel($data);

        return $noticeModel;
    }

    public static function createGeneralBoard($requestData)
    {
        $data = [
            'title' => $requestData['title'],
            'content' => $requestData['content'],
            'author' => $requestData['author'],
            'general_type' => $requestData['general_type'],
        ];

        $generalModel = new GeneralBoardModel($data);

        return $generalModel;
    }

    public static function createAnonymousBoard($requestData)
    {
        $data = [
            'title' => $requestData['title'],
            'content' => $requestData['content'],
            'anonymous_type' => $requestData['anonymous_type'],
        ];

        $anonymousModel = new AnonymousBoardModel($data);

        return $anonymousModel;
    }
}

//Factory는 단순히 type에 따라 분기해서 알맞는 객체를 생성하는 mapper를 호출한다.
class BoardFactory
{
    public static function createBoard($type, $requestData)
    {
        switch ($type) {
            case 'notice':
                return BoardMapper::createNoticeBoard($requestData);
            case 'general':
                return BoardMapper::createGeneralBoard($requestData);
            case 'anonymous':
                return BoardMapper::createAnonymousBoard($requestData);
            default:
                return null;
        }
    }
}

```

## 🔆 Mapper

> 조사를 해보니 <br>   1. 데이터베이스 상호 작용을 위한 Mapper <br>   2. Converting을 하기위한 Mapper <br>두 종류가 있었다. (둘이 다르다. 헷갈리지 말자)

우리가 알아야할 Converting을 위한 Mapper에 자세히 적힌 참고자료가 있어서 가져왔다.<br>⭐참조 자료 : [https://velog.io/@given53/Spring-Mapper](https://velog.io/@given53/Spring-Mapper)<br>⭐참조 자료 : [https://velog.io/@0sunset0/Dto와-Entity를-분리하는-이유-분리하는-방법](https://velog.io/@0sunset0/Dto%EC%99%80-Entity%EB%A5%BC-%EB%B6%84%EB%A6%AC%ED%95%98%EB%8A%94-%EC%9D%B4%EC%9C%A0-%EB%B6%84%EB%A6%AC%ED%95%98%EB%8A%94-%EB%B0%A9%EB%B2%95)<br><br>찾아보니 많은 사람들이 DTO→Entity, Entity→DTO 를 어떤 layer에서 해결해야하는 지 고민이 많았다.<br>그렇다보니 명확히 어떤 layer에서 해야해 ! 라는 것은 없었지만,<br>Service에서 변환해주는 것이 맞고(변환로직호출) Mapper에게 변환에 대한 책임을 위임하는 것이 좋다고 결론을 내렸다.<br>

-  만약에 사용자로부터 받은 request의 key 이름이 바뀌었다고 하자.

  - 그러면 이 key를 사용하는 부분을 찾아서 수정해야하기에 Controller에서 변환을 했다면 찾기에는 가장 빠를 것이다.<br>하지만 이때에는 도메인 로직이 표현계층에 존재하는 부담과 Controller에서 너무 많은 코드들이 들어갈 것이다. <br>→ Controller 탈락
  - Service에서 동일한 작업을 할때에는 key가 어디서 쓰이고 있는 지 찾아야한다. <br>코드 분석에 많은 시간이 소요된다 ….<br>하지만 도메인 로직이 표현계층에 전달되지 않도록 할 수 있기때문에 보안상 좋다.<br>→ 애매하지만 장점은 분명히 있다.
  - Repository에서는<br>Aggregate의 영속성과 Repository 자체만을 고려해야한다. 이로 인해, DTO가 Repository 단까지 진입하는 것은 지양하자는 의견이 지배적이다.<br>→ 절대 안쓰는 것으로..

  ### ⁕ **다 애매한데 어디서 쓰지🤣 ?**

  1\. 변환에 대한 로직을 DTO안에 넣는다면 ? <br>: Entity정보도 DTO에 혼용될 것이고 책임이 모호해질뿐만 아니라 같은 DTO를 이용해 다른 Entity를 만들 수도 있다면<br>DTO는 단순히 Request, Response를 위한 형태일 뿐.. 공통 DTO가 있다면 어디서 Entity를 컨버팅해야할 지 찾아야한다.<br>(DTO에서 Entity 객체를 생성한다니 이상하지 않은가 - 놀랍게도 실제로 많이 쓰인다고 한다.)<br><br> 2. **모든 변환에 대한 책임은 Mapper로 !**<br>: 음 ? key값 바뀌었는데  어디어디 고쳐야하지,, 해당 DTO 필드와 DTO를 넘겨받고 있는 Mapper만 찾아가서 고치면 끝 !<br>

> 마틴 파울러는 **Service Layer**란 애플리케이션의 경계를 정의하고 비즈니스 로직 등 Domain을 캡슐화하는 역할이라고 정의한다.<br>이 정의에 따르면 표현 계층에 Domain을 노출해선 안된다. 따라서 Domain은 Service에서 DTO로 변환되어 Controller로 전달되어야 한다.

위 인용에 따라 Entity정보는 Controller로 나가서는 안된다. → DTO로 변환해서 나가야한다.<br><br>⭐참조 자료 : [https://velog.io/@0sunset0/Dto와-Entity를-분리하는-이유-분리하는-방법](https://velog.io/@0sunset0/Dto%EC%99%80-Entity%EB%A5%BC-%EB%B6%84%EB%A6%AC%ED%95%98%EB%8A%94-%EC%9D%B4%EC%9C%A0-%EB%B6%84%EB%A6%AC%ED%95%98%EB%8A%94-%EB%B0%A9%EB%B2%95)

<br><br>

<details>
<summary>⁕ Factory Pattern의 종류와 JAVA에서 일반적인 사용 예시</summary>

- 심플 팩토리 패턴

```java
//휴대폰을 만드는 공장
public class SimplePhoneFactory {
    public Phone orderPhone(String type) {
        Phone phone = createPhone(type);
        phone.complete();
        return phone;
    }
    private Phone createPhone(String type) {
        return switch (type) {
            case "IPHONE" -> new IPhone();
            case "ANDROID" -> new AndroidPhone();
            default -> null;
        };
    }
}

//휴대폰 인터페이스
public interface Phone {
    void complete();
    void call();
}

//아이폰
public class IPhone implements Phone{
    @Override
    public void complete() {
        System.out.println("아이폰 완성");
    }

    @Override
    public void call() {
        System.out.println("아이폰으로 전화를 한다");
    }
}

//안드로이드 폰
public class AndroidPhone implements Phone{
    @Override
    public void complete() {
        System.out.println("안드로이드폰 완성");
    }

    @Override
    public void call() {
        System.out.println("안드로이드폰으로 전화를 한다");
    }
}

//클라이언트는 휴대폰 공장에 휴대폰을 주문한다.
public class Practice {
    public static void main(String[] args){
        SimplePhoneFactory simplePhoneFactory = new SimplePhoneFactory();
        Phone phone = simplePhoneFactory.orderPhone("ANDROID");
        phone.call();
    }
}

//결과
안드로이드폰 완성
안드로이드폰으로 전화를 한다
```

- 팩토리 메소드 패턴

```java
// 팩토리 인터페이스
public interface PhoneFactory {
    default Phone orderPhone() {
        Phone phone = createPhone();
        phone.complete();
        return phone;
    }
    Phone createPhone();
}

// IPhone 팩토리
public class IPhoneFactory implements PhoneFactory {
    @Override
    public Phone createPhone() {
        return new IPhone();
    }
}

// Android 팩토리
public class AndroidPhoneFactory implements PhoneFactory {
    @Override
    public Phone createPhone() {
        return new AndroidPhone();
    }
}

public interface Phone {
    void complete();
    void call();
}
public class IPhone implements Phone{
    @Override
    public void complete() { System.out.println("아이폰 완성"); }
    @Override
    public void call() { System.out.println("아이폰으로 전화를 한다"); }
}
public class AndroidPhone implements Phone{
    @Override
    public void complete() {System.out.println("안드로이드폰 완성");}
    @Override
    public void call() {System.out.println("안드로이드폰으로 전화를 한다");}
}

public class Practice {
    public static void main(String[] args){
        IPhoneFactory iPhoneFactory = new IPhoneFactory();
        Phone phone7 = iPhoneFactory.orderPhone();
        phone7.call();

        AndroidPhoneFactory androidPhoneFactory = new AndroidPhoneFactory();
        Phone phone2 = androidPhoneFactory.orderPhone();
        phone2.call();
    }
}

//결과
아이폰 완성
아이폰으로 전화를 한다
안드로이드폰 완성
안드로이드폰으로 전화를 한다
```

- 추상 팩토리 패턴

```java
///
public interface PhoneFactoryOfFactory {
    PhoneFactory requestPhone(String company);
}
public class DefaultPhoneFactoryOfFactory implements PhoneFactoryOfFactory{
    @Override
    public PhoneFactory requestPhone(String company) {
        switch (company) {
            case "IPHONE":
                return new IPhoneFactory();
            case "ANDROID":
                return new AndroidPhoneFactory();
        }
        throw new IllegalArgumentException();
    }
}
///

///
public interface PhoneFactory {
    Phone createPhone();
    OS createOS();
}
public class IPhoneFactory implements PhoneFactory{
    @Override
    public Phone createPhone() {
        OS os = createOS();
        os.installOS();
        return new IPhone();
    }
    @Override
    public OS createOS() {
        return new IOS();
    }
}
///
public class AndroidPhoneFactory implements PhoneFactory{
    @Override
    public Phone createPhone() {
        OS os = createOS();
        os.installOS();
        return new AndroidPhone();
    }
    @Override
    public OS createOS() {
        return new GoogleOS();
    }
}
///

///
public interface OS {
    void installOS();
}
public class IOS implements OS {
    @Override
    public void installOS() {
        System.out.println("IOS 설치");
    }
}
public class GoogleOS implements OS {
    @Override
    public void installOS() {
        System.out.println("구글OS 설치");
    }
}

///
public interface Phone {
    public void call();
    public void playGame();
}
public class IPhone implements Phone{
    @Override
    public void call() {
        System.out.println("아이폰으로 전화하다");
    }

    @Override
    public void playGame() {
        System.out.println("아이폰으로 게임하다");
    }
}
///
public class AndroidPhone implements Phone{
    @Override
    public void call() {
        System.out.println("안드로이드로 전화하다");
    }

    @Override
    public void playGame() {
        System.out.println("안드로이드로 게임하다");
    }
}
///
public class Main {
    public static void main(String[] args) {
        PhoneFactoryOfFactory phoneFactoryOfFactory = new DefaultPhoneFactoryOfFactory();
        PhoneFactory iphoneFactory= phoneFactoryOfFactory.requestPhone("IPHONE");   //아이폰을 산다.
        Phone iphone = iphoneFactory.createPhone();
        iphone.call();
        iphone.playGame();

        PhoneFactory androidPhoneFactory = phoneFactoryOfFactory.requestPhone("ANDROID");   //안드로이드폰을 산다.
        Phone androidPhone = androidPhoneFactory.createPhone();
        androidPhone.call();
        androidPhone.playGame();
    }
}

//결과
IOS 설치
아이폰으로 전화하다
아이폰으로 게임하다
구글OS 설치
안드로이드로 전화하다
안드로이드로 게임하다
```

</details>
