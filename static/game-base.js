function setMessage(msg, type) {
    var el = document.getElementById('message')
    el.className = el.className.replace(/ ?type-\w+/g, '')
    el.className += ' type-' + type
    el.innerHTML = msg
    el.removeChild(el.firstChild)
    el.appendChild(document.createTextNode(String(msg)))
}

var wsHost = document.location.hostname + ":" + 8080,
    ws     = new WebSocket("ws://{}/websocket".replace(/{}/, wsHost))

var state = 'spectating'

ws.onmessage = function (evt) {
    var obj = JSON.parse(evt.data)

    if      (obj.error   != null) setMessage(obj.error,   'error')
    else if (obj.message != null) setMessage(obj.message, 'message')

    if      (obj.state   != null) state = obj.state

    on_message(obj)
    handle_queue_msg(obj)
};

var table = document.getElementById("grid");
for(var i=0; i < config.grid_y; i++) {
    // Create tr
    var tr = document.createElement("tr");
    for(var ii=0; ii < config.grid_x; ii++) {
        // Add td and function onclick
        var td = document.createElement("td");
        tr.appendChild(td);

        var img = document.createElement('img')
        img.src = '/static/lamp.png'
        img.id  = ii + '-' + i
        img.className += ' tile'
        img.onclick = play
        td.appendChild(img)
    }

    // Add tr to DOM
    table.appendChild(tr);
}

function handle_queue_msg(obj) {
    if (obj.queuepos != undefined) {
        qmsg = document.getElementById("queuemsg")
        qbtn = document.getElementById("queuebtn")
        if(obj.queuepos > 0) {
            qmsg.innerHTML = "Your place in queue: " + obj.queuepos;
            qbtn.value = "Leave queue";
            qbtn.onclick = function() {
                ws.send(JSON.stringify({ queueaction : 0 }));
            }
        } else {
            qmsg.innerHTML = "You are not in the queue";
            qbtn.value = "Join queue";
            qbtn.onclick = function() {
                ws.send(JSON.stringify({ queueaction : 1 }));
            }
        }
    }
}
