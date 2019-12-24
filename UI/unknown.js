var chatHistory = [];
receiveMessageFromApi("check me in");
function sendMessageToApi(){
  //alert("Inside sendMessageToApi");

  var inputText = document.getElementById('user-input-message').value.trim().toLowerCase();

  document.getElementById('user-input-message').value = "";

  if(inputText == "") {
    //alert("Please enter some text");
    return false;
  }else {

    chatHistory.push('<b><color = "red">User:</color> </b>' + inputText);

    document.getElementById('bot-response').innerHTML = "";

    chatHistory.forEach((element) => {
      document.getElementById('bot-response').innerHTML += "<p>" + element + "</p>";
    });
    receiveMessageFromApi(inputText);
    //alert('after calling function');
    return false;
  }

}

function receiveMessageFromApi(inputText){
    apigClient = apigClientFactory.newClient({
      // accessKey: 'AKIAIVIHZAIXOL7BR7RA',
      // secretKey: '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'
    });
    var faceid = localStorage.getItem("faceid");

    var params = {};
    var body = {
      "userId" : "123",
      "message":inputText,
      "faceid" : faceid
    };

    var additionalParams = {
      headers: {
        
      },
      queryParams: {}
    };

    apigClient.unknownPost(params,body,additionalParams).then((result) =>{

      //alert("Inside return api client");
      console.log(result);
      chatHistory.push('<b><color = "Cyan">Bot:</color> </b>' + JSON.stringify(result.data.message));
      document.getElementById('bot-response').innerHTML = "";
      chatHistory.forEach((element) => {
        document.getElementById('bot-response').innerHTML += "<p>" +element + "</p>";
      });
      var bot=result.data.message;
      if(bot.includes("Welcome", 0))
        {
          document.getElementById("container").innerHTML=bot;
          document.getElementById("container").style.fontSize = "xx-large";
        }
  
  })
  .catch((err) =>{
    console.log(err);
  });

}
