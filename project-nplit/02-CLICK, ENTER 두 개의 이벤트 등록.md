# CLICK, ENTER 두 개의 이벤트 등록

> 작성: 2021-12-28 · [노션 원본](https://app.notion.com/p/2ff5118c8a8c4778a084e4090377131d)

### 채팅을 보낼 때 전송 버튼을 클릭해야만 메세지 전송이 되는데, ENTER를 눌러도 전송이 되게 수정하려고 했다.

```javascript
/*기존 코드*/

$("#button-send").on("click", function (e) {
  
            var msg = document.getElementById("msg");

            console.log(username + ":" + msg.value);
            stomp.send('/pub/chat/message', {}, JSON.stringify({roomId: roomId, message: msg.value, sendId: username, fullFilePath: [[${session.login.fullFilePath}]]}));
            msg.value = '';
  
         });
```

```javascript
/*기존 코드 밑에 추가된 코드*/
$("#msg").keydown( function (key) {
             if (key.keyCode == 13) {
             var msg = document.getElementById("msg");
  
             console.log(username + ":" + msg.value);
             stomp.send('/pub/chat/message', {}, JSON.stringify({roomId: roomId, message: msg.value, sendId: username, fullFilePath: [[${session.login.fullFilePath}]]}));
             msg.value = '';
             }
           });
```

- 기존 코드가 클릭만으로 메세지 전송을 했고 ENTER로도 메세지 전송이 되도록 했다
- html파일의 적용할 input박스 id가 msg기때문에 msg라는 아이디로 엔터에 관련된 keydown(키가 눌렸을때 반응하는 이벤트) 이벤트를 추가해주고 keyCode==13(엔터의 번호)일 때 버튼이 눌렸을 때와 같은 내용을 적용시키면 ENTER, CLICK 모두 반응한다.
