/* token */
const token = document.querySelector("body").dataset.token;

/* insert js-only markup */
const jsmarkup_style = '<style id="style_js"></style>'
const jsmarkup_info = '<div id="info_js"></div>';
const jsmarkup_info_title = '<header id="info_js__title" data-js="true"></header>';
const jsmarkup_chat_messages = '<ul id="chat-messages_js" data-js="true"></ul>';
const jsmarkup_chat_form = `\
  <form id="chat-form_js" data-js="true" action="/chat" method="post">
  <input id="chat-form_js__nonce" type="hidden" name="nonce" value="">
  <textarea id="chat-form_js__comment" name="comment" maxlength="512" required placeholder="Send a message..." rows="1"></textarea>
  <div id="chat-live">
    <span id="chat-live__ball"></span>
    <span id="chat-live__status">Not connected to chat</span>
  </div>
  <input id="chat-form_js__submit" type="submit" value="Chat" accesskey="p" disabled>
  </form>`;

const insert_jsmarkup = () => {
  if (document.getElementById("style_js") === null) {
    const parent = document.head;
    parent.insertAdjacentHTML("beforeend", jsmarkup_style);
  }
  if (document.getElementById("info_js") === null) {
    const parent = document.getElementById("info");
    parent.insertAdjacentHTML("beforeend", jsmarkup_info);
  }
  if (document.getElementById("info_js__title") === null) {
    const parent = document.getElementById("info_js");
    parent.insertAdjacentHTML("beforeend", jsmarkup_info_title);
  }
  if (document.getElementById("chat-messages_js") === null) {
    const parent = document.getElementById("chat__messages");
    parent.insertAdjacentHTML("beforeend", jsmarkup_chat_messages);
  }
  if (document.getElementById("chat-form_js") === null) {
    const parent = document.getElementById("chat__form");
    parent.insertAdjacentHTML("beforeend", jsmarkup_chat_form);
  }
}

insert_jsmarkup();
const stylesheet = document.styleSheets[1];

/* create websocket */
const info_title = document.getElementById("info_js__title");
const chat_messages = document.getElementById("chat-messages_js");

const create_chat_message = (object) => {
  const user = users[object.token_hash];

  const chat_message = document.createElement("li");
  chat_message.classList.add("chat-message");
  chat_message.dataset.seq = object.seq;
  chat_message.dataset.tokenHash = object.token_hash;

  const chat_message_name = document.createElement("span");
  chat_message_name.classList.add("chat-message__name");
  chat_message_name.innerText = user.name || default_name[user.broadcaster];
  //chat_message_name.dataset.color = user.color; // not working in any browser

  const chat_message_markup = document.createElement("span");
  chat_message_markup.classList.add("chat-message__markup");
  chat_message_markup.innerHTML = object.markup;

  chat_message.insertAdjacentElement("beforeend", chat_message_name);
  chat_message.insertAdjacentHTML("beforeend", ":&nbsp;");
  chat_message.insertAdjacentElement("beforeend", chat_message_markup);

  return chat_message
}

let users = {};
let default_name = {true: "Broadcaster", false: "Anonymous"};
const equal = (color1, color2) => {
  /* comparing css colors is annoying */
  return false;
}
const update_user_styles = () => {
  const to_delete = [];
  const to_ignore = new Set();
  for (let index = 0; index < stylesheet.cssRules.length; index++) {
    const css_rule = stylesheet.cssRules[index];
    const match = css_rule.selectorText.match(/.chat-message\[data-token-hash="([a-z2-7]{26})"\] > .chat-message__name/);
    const token_hash = match === null ? null : match[1];
    const user = token_hash === null ? null : users[token_hash];
    if (user === null || user === undefined) {
      to_delete.push(index);
    } else if (!equal(css_rule.style.color, user.color)) {
      to_delete.push(index);
    } else {
      to_ignore.add(token_hash);
    }
  }

  for (const token_hash of Object.keys(users)) {
    if (!to_ignore.has(token_hash)) {
      const user = users[token_hash];
      stylesheet.insertRule(
        `.chat-message[data-token-hash="${token_hash}"] > .chat-message__name { color: ${user.color}; }`,
        stylesheet.cssRules.length,
      );
    }
  }
  for (const index of to_delete.reverse()) {
    stylesheet.deleteRule(index);
  }
}

const on_websocket_message = (event) => {
  console.log("websocket message", event);
  const receipt = JSON.parse(event.data);
  switch (receipt.type) {
    case "error":
      console.log("ws error", receipt);
      break;

    case "init":
      console.log("ws init", receipt);

      chat_form_nonce.value = receipt.nonce;
      info_title.innerText = receipt.title;

      default_name = receipt.default;
      users = receipt.users;
      update_user_styles();

      const seqs = new Set(receipt.messages.map((message) => {return message.seq;}));
      const to_delete = [];
      for (const chat_message of chat_messages.children) {
        const chat_message_seq = parseInt(chat_message.dataset.seq);
        if (!seqs.has(chat_message_seq)) {
          to_delete.push(chat_message);
        }
      }
      for (const chat_message of to_delete) {
        chat_message.remove();
      }

      const last = chat_messages.children.length == 0 ? null : chat_messages.children[chat_messages.children.length - 1];
      const last_seq = last === null ? null : parseInt(last.dataset.seq);
      for (const message of receipt.messages) {
        if (message.seq > last_seq) {
          const chat_message = create_chat_message(message);
          chat_messages.insertAdjacentElement("beforeend", chat_message);
        }
      }

      break;

    case "title":
      console.log("ws title", receipt);
      info_title.innerText = receipt.title;
      break;

    case "ack":
      console.log("ws ack", receipt);
      if (chat_form_nonce.value === receipt.nonce) {
        chat_form_comment.value = "";
      } else {
        console.log("nonce does not match ack", chat_form_nonce, receipt);
      }
      chat_form_submit.disabled = false;
      chat_form_nonce.value = receipt.next;
      break;

    case "reject":
      console.log("ws reject", receipt);
      alert(`Rejected: ${receipt.notice}`);
      chat_form_submit.disabled = false;
      chat_form_nonce.value = receipt.next;
      break;

    case "chat":
      console.log("ws chat", receipt);
      const chat_message = create_chat_message(receipt);
      chat_messages.insertAdjacentElement("beforeend", chat_message);
      chat_messages.scrollTo({
        left: 0,
        top: chat_messages.scrollTopMax,
        behavior: "smooth",
      });
      break;

    case "add-user":
        console.log("ws add-user", receipt);
        users[receipt.token_hash] = receipt.user;
        update_user_styles();
        break;

    case "rem-users":
        console.log("ws rem-users", receipt);
        for (const token_hash of receipt.token_hashes) {
          delete users[token_hash];
        }
        update_user_styles();
        break;

    default:
      console.log("incomprehensible websocket message", receipt);
  }
};
const chat_live_ball = document.getElementById("chat-live__ball");
const chat_live_status = document.getElementById("chat-live__status");
let ws;
let websocket_backoff = 2000; // 2 seconds
const connect_websocket = () => {
  if (ws !== undefined && (ws.readyState === ws.CONNECTING || ws.readyState === ws.OPEN)) {
    console.log("refusing to open another websocket");
    return;
  }
  chat_live_ball.style.borderColor = "gold";
  chat_live_status.innerText = "Connecting to chat...";
  ws = new WebSocket(`ws://${document.domain}:${location.port}/live?token=${encodeURIComponent(token)}`);
  ws.addEventListener("open", (event) => {
    console.log("websocket open", event);
    chat_form_submit.disabled = false;
    chat_live_ball.style.borderColor = "green";
    chat_live_status.innerText = "Connected to chat";
    // When the server is offline, a newly opened websocket can take a second
    // to close. This timeout tries to ensure the backoff doesn't instantly
    // (erroneously) reset to 2 seconds in that case.
    setTimeout(() => {
        if (event.target === ws) {
          websocket_backoff = 2000; // 2 seconds
        }
      },
      websocket_backoff + 4000,
    );
  });
  ws.addEventListener("close", (event) => {
    console.log("websocket close", event);
    chat_form_submit.disabled = true;
    chat_live_ball.style.borderColor = "maroon";
    chat_live_status.innerText = "Disconnected from chat";
    if (!ws.successor) {
      ws.successor = true;
      setTimeout(connect_websocket, websocket_backoff);
      websocket_backoff = Math.min(32000, websocket_backoff * 2);
    }
  });
  ws.addEventListener("error", (event) => {
    console.log("websocket error", event);
    chat_form_submit.disabled = true;
    chat_live_ball.style.borderColor = "maroon";
    chat_live_status.innerText = "Error connecting to chat";
  });
  ws.addEventListener("message", on_websocket_message);
}

connect_websocket();

/* override js-only chat form */
const chat_form = document.getElementById("chat-form_js");
const chat_form_nonce = document.getElementById("chat-form_js__nonce");
const chat_form_comment = document.getElementById("chat-form_js__comment");
const chat_form_submit = document.getElementById("chat-form_js__submit");
chat_form.addEventListener("submit", (event) => {
  event.preventDefault();
  const payload = {comment: chat_form_comment.value, nonce: chat_form_nonce.value};
  chat_form_submit.disabled = true;
  ws.send(JSON.stringify(payload));
});

/* when chat is being resized, peg its bottom in place (instead of its top) */
const track_scroll = (element) => {
  chat_messages.dataset.scrollTop = chat_messages.scrollTop;
  chat_messages.dataset.scrollTopMax = chat_messages.scrollTopMax;
}
const peg_bottom = (entries) => {
  for (const entry of entries) {
    const element = entry.target;
    const bottom = chat_messages.dataset.scrollTopMax - chat_messages.dataset.scrollTop;
    element.scrollTop = chat_messages.scrollTopMax - bottom;
    track_scroll(element);
  }
}
const resize = new ResizeObserver(peg_bottom);
resize.observe(chat_messages);
chat_messages.addEventListener("scroll", (event) => {
  track_scroll(chat_messages);
});
track_scroll(chat_messages);
