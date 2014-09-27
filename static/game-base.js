/*
 * Playhouse: Making buildings into interactive displays using remotely controllable lights.
 * Copyright (C) 2014  John Eriksson, Arvid Fahlström Myrman, Jonas Höglund,
 *                     Hannes Leskelä, Christian Lidström, Mattias Palo, 
 *                     Markus Videll, Tomas Wickman, Emil Öhman.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

//-- Websocket/grid setup -----------------------
var wsHost = document.location.hostname + ":" + socketport,
    ws     = new WebSocket("ws://{}/websocket".replace(/{}/, wsHost))

var state = 'spectating'

ws.onclose = function(evt) {
    if(state != 'destroyed') {
        showOverlay("Game destroyed, reloading...")
    }
    setTimeout(function(){location.reload()},2000);
}; 

ws.onmessage = function (evt) {
    var obj = JSON.parse(evt.data)

    if (obj.overlaymessage != null) {
        showOverlay(obj.overlaymessage)
    }

    if (obj.state != null) {
        state = obj.state
        if (state == 'destroyed') {
                setTimeout(function(){location.reload()},2000);
        }
    }

    if (obj.message != null) setMessage(obj.message, 'message')
    if (obj.error   != null) setMessage(obj.error,   'error')

    on_message(obj)
};

function buildGrid(w, h) {
    var table = document.getElementById("grid");
    table.innerHTML = ""

    for(var i=0; i < h; i++) {
        // Create tr
        var tr = document.createElement("tr");

        if (templateConfig.paddingCells) {
            tr.appendChild(document.createElement('td'))
        }

        for(var ii=0; ii < w; ii++) {
            // Add td and function onclick
            var tmp = createLampEl('td'),
                td  = tmp[0],
                el  = tmp[1]

            el.id          = ii + '-' + i
            el.onclick     = play
            el.classList.add('tile')

            tr.appendChild(td);
        }

        if (templateConfig.paddingCells) {
            tr.appendChild(document.createElement('td'))
        }

        // Add tr to DOM
        table.appendChild(tr);
    }
}

buildGrid(config.grid_x, config.grid_y)


//-- Overlay ------------------------------------
function showOverlay(msg) {
    document.getElementById('overlaymessage').innerHTML = msg
    var over = document.getElementById("overlay")
    over.className = ""
    setTimeout(function(){over.className="hidden"}, 3000)
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

    qbtn.disabled = (state == 'playing' || state == 'destroyed')

    if (state == 'destroyed') {
        qbtn.onclick = function() {}

    } else if (state == 'playing') {
        qbtn.value = "In game";
        qbtn.onclick = function() {}

    } else if (obj.queuepos > 0) {
        setMessage("Your place in queue: " + obj.queuepos, 'message')
        state = 'spectating'
        qbtn.value = "Leave queue";
        qbtn.onclick = function() {
            ws.send(JSON.stringify({ session : session, queueaction : 0 }));
        }

    } else if (state == 'gameover' || obj.queuepos == 0) {
        if (obj.queuepos == 0) {
            setMessage("You are a spectator!", 'message')
            state = 'spectating'
        }
        qbtn.value = "Join queue";
        qbtn.onclick = function() {
            ws.send(JSON.stringify({ session : session, queueaction : 1 }));
        }
    }
}


//-- Rules --------------------------------------
/*var rulesEl = document.getElementById('rules')
rules.style.display = 'none'

function showButton() {
    if (rulesEl.style.display != 'block') {
        rulesEl.style.display = 'block'
        rulesEl.scrollIntoView()
    } else {
        rulesEl.style.display = 'none'
    }
}*/
