import Guacamole from './js/guacamole-common.min.js';

const urlParams = new URLSearchParams(window.location.search);
const instanceID = urlParams.get('instance_id');
const guacToken = urlParams.get('guac_token');

const url = new URL("/desktop/" + instanceID + "/vnc/websockify", window.location.href);
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

const tunnel = new Guacamole.WebSocketTunnel(`${protocol}//${url.host}${url.pathname}`);
const guac = new Guacamole.Client(tunnel);

const display = document.body.appendChild(guac.getDisplay().getElement());
display.setAttribute('tabindex', '0');
display.style.outline = 'none';
display.addEventListener('mousedown', () => display.focus());

const keyboard = new Guacamole.Keyboard(display);
keyboard.onkeydown = keysym => guac.sendKeyEvent(1, keysym);
keyboard.onkeyup = keysym => guac.sendKeyEvent(0, keysym);

const mouse = new Guacamole.Mouse(guac.getDisplay().getElement());
mouse.onmousedown =
mouse.onmousemove =
mouse.onmouseup   = state => {
    guac.sendMouseState(state);
};

guac.getDisplay().onresize = (w, h) => {
    console.log('[guac] display resize:', w, 'x', h);
};

guac.onerror = error => {
    console.error('[guac] error:', error.message);
    window.parent.postMessage({ action: 'connection_state', value: 'disconnected', error: error.message }, '*');
};

guac.onstatechange = state => {
    const names = ['IDLE','CONNECTING','WAITING','CONNECTED','DISCONNECTING','DISCONNECTED'];
    console.log('[guac] state:', names[state] ?? state);
    switch(state) {
        case 0:
        case 1:
        case 2:
            window.parent.postMessage({ action: 'connection_state', value: 'connecting' }, '*');
            break;
        case 3:
            window.parent.postMessage({ action: 'connection_state', value: 'connected' }, '*');
            display.focus();
            break;
        case 4:
        case 5:
            window.parent.postMessage({ action: 'connection_state', value: 'disconnected' }, '*');
            break;
    }
};

// Remote → local clipboard: send text to parent control panel via postMessage
guac.onclipboard = (stream, mimetype) => {
    if (!mimetype.startsWith('text/')) return;
    let data = '';
    const reader = new Guacamole.StringReader(stream);
    reader.ontext = text => data += text;
    reader.onend = () => {
        console.log('[guac] clipboard received from remote:', data.length, 'chars');
        window.parent.postMessage({ action: 'clipboardrx', value: data }, '*');
    };
};

// Local → remote clipboard: receive text from parent control panel via postMessage
window.addEventListener('message', (event) => {
    if (event.data?.action === 'clipboardsnd') {
        const text = event.data.value;
        if (typeof text === 'string' && text.length > 0) {
            const stream = guac.createClipboardStream('text/plain');
            const writer = new Guacamole.StringWriter(stream);
            writer.sendText(text);
            writer.sendEnd();
            console.log('[guac] clipboard sent to remote:', text.length, 'chars');
        }
    }
});

const GUAC_WIDTH  = Math.round(window.innerWidth);
const GUAC_HEIGHT = Math.round(window.innerHeight);

guac.connect(`token=${encodeURIComponent(guacToken)}&width=${GUAC_WIDTH}&height=${GUAC_HEIGHT}`);

const resizeDisplay = () => {
    const GUAC_WIDTH  = Math.round(window.innerWidth);
    const GUAC_HEIGHT = Math.round(window.innerHeight);
    tunnel.sendMessage('size', GUAC_WIDTH, GUAC_HEIGHT)
}

window.onresize = resizeDisplay;
