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
    var el = document.getElementById('message')
    el.style.transition = ''
    replaceClass(el, 'type-\\w+', 'type-' + type)
    el.innerHTML = msg

    if (type != 'error') {
      savedMessage = el.innerHTML
    } else {
      setTimeout(function () {
        replaceClass(el, 'type-\\w+', 'type-message')
        el.innerHTML = savedMessage
      }, 3500)
    }
}


//-- Queue --------------------------------------
function handle_queue_msg(obj) {
    qmsg = document.getElementById("queuemsg")
    qbtn = document.getElementById("queuebtn")
    if (obj.state != null) {
        qbtn.disabled = state == 'playing'
        if (state == 'playing') {
            qmsg.innerHTML = "You are currently playing";
            qbtn.value = "Leave game";
            qbtn.onclick = function() {}
        } else if (obj.queuepos == undefined) {
            obj.queuepos = 0
        }
    }
    if (obj.queuepos != undefined) {
        if (obj.queuepos > 0) {
            qmsg.innerHTML = "Your place in queue: " + obj.queuepos;
            qbtn.value = "Leave queue";
            qbtn.onclick = function() {
                ws.send(JSON.stringify({ session : session, queueaction : 0 }));
            }
        } else {
            qmsg.innerHTML = "You are not in the queue";
            qbtn.value = "Join queue";
            qbtn.onclick = function() {
                ws.send(JSON.stringify({ session : session, queueaction : 1 }));
            }
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
