//-- Websocket/grid setup -----------------------
var wsHost = document.location.hostname + ":" + socketport,
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

function ignoreEvent(ev) {
  ev.preventDefault()
  return false
}

var table = document.getElementById("grid");
for(var i=0; i < config.grid_y; i++) {
    // Create tr
    var tr = document.createElement("tr");
    for(var ii=0; ii < config.grid_x; ii++) {
        // Add td and function onclick
        var td = document.createElement("td");
        tr.appendChild(td);

        var img = document.createElement('img')
        img.src         = '/static/lamp.png'
        img.draggable   = false
        img.id          = ii + '-' + i
        img.onclick     = play
        img.ondragstart = ignoreEvent
        img.classList.add('tile')
        td.appendChild(img)
    }

    // Add tr to DOM
    table.appendChild(tr);
}


//-- Messages -----------------------------------
function replaceClass(el, pattern, newClass) {
  el.className = el.className.replace(new RegExp(" ?" + pattern + "|$"), " " + newClass)
}

var savedMessage = "Loading..."
function setMessage(msg, type) {
    var boxEl = document.getElementById('message-box'),
        msgEl = document.getElementById('message')
    replaceClass(boxEl, 'type-\\w+', 'type-' + type)
    msgEl.innerHTML = msg

    if (type != 'error') {
      savedMessage = msgEl.innerHTML
    } else {
      setTimeout(function () {
        replaceClass(boxEl, 'type-\\w+', 'type-message')
        msgEl.innerHTML = savedMessage
      }, 3500)
    }
}


//-- Queue --------------------------------------
function handle_queue_msg(obj) {
    var qbtn = document.getElementById("queuebtn")

    qbtn.disabled = (state == 'playing')

    if (state == 'playing') {
        qbtn.value = "In game";
        qbtn.onclick = function() {}

    } else if (obj.queuepos > 0) {
        setMessage("Your place in queue: " + obj.queuepos, 'message')
        qbtn.value = "Leave queue";
        qbtn.onclick = function() {
            ws.send(JSON.stringify({ session : session, queueaction : 0 }));
        }

    } else if (state == 'gameover' || obj.queuepos == 0) {
        if (obj.queuepos == 0) {
            setMessage("You are a spectator!", 'message')
        }
        qbtn.value = "Join queue";
        qbtn.onclick = function() {
            ws.send(JSON.stringify({ session : session, queueaction : 1 }));
        }
    }
}


//-- Rules --------------------------------------
var rulesEl = document.getElementById('rules')
rules.style.display = 'none'

function showButton() {
    if (rulesEl.style.display != 'block') {
        rulesEl.style.display = 'block'
        rulesEl.scrollIntoView()
    } else {
        rulesEl.style.display = 'none'
    }
}
