function createLampEl(tag) {
    // Add td and function onclick
    var resEl = document.createElement(tag)

    var el = resEl
    if (templateConfig.imageCells) {
        el = document.createElement('img')
        el.src       = '/static/lamp.png'
        el.draggable = false
        el.ondragstart = ignoreEvent
        resEl.appendChild(el)
    }

    return [ resEl, el ]
}

function ignoreEvent(ev) {
  ev.preventDefault()
  return false
}
