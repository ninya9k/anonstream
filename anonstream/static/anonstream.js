/**
 * SPDX-FileCopyrightText: 2022 n9k [https://git.076.ne.jp/ninya9k]
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

/* token */
const TOKEN = document.body.dataset.token;
const TOKEN_HASH = document.body.dataset.tokenHash;

/* Content Security Policy nonce */
const CSP = document.body.dataset.csp;

/* insert js-only markup */
const jsmarkup_stream = `<video id="stream_js" src="/stream.mp4?token=${encodeURIComponent(TOKEN)}" autoplay controls></video>`
const jsmarkup_info = '<div id="info_js" data-js="true"></div>';
const jsmarkup_info_float = '<aside id="info_js__float"></aside>';
const jsmarkup_info_float_button = '<button id="info_js__float__button">Reload stream</button>';
const jsmarkup_info_float_viewership = '<div id="info_js__float__viewership"></div>';
const jsmarkup_info_float_uptime = '<div id="info_js__float__uptime"></div>';
const jsmarkup_info_title = '<header id="info_js__title"></header>';
const jsmarkup_chat_messages = '<ol id="chat-messages_js" data-js="true"></ol>';
const jsmarkup_chat_users = `\
<article id="chat-users_js">
  <h5 id="chat-users_js__watching-header"></h5>
  <ul id="chat-users_js__watching"></ul>
  <br>
  <h5 id="chat-users_js__notwatching-header"></h5>
  <ul id="chat-users_js__notwatching"></ul>
</article>`;
const jsmarkup_chat_form = `\
<form id="chat-form_js" data-js="true" action="/chat" method="post">
  <input id="chat-form_js__nonce" type="hidden" name="nonce" value="">
  <textarea id="chat-form_js__comment" name="comment" maxlength="512" required placeholder="Send a message..." rows="1" autofocus></textarea>
  <div id="chat-live">
    <span id="chat-live__ball"></span>
    <span id="chat-live__status">
      <span data-verbose="true">Not connected to chat</span>
      <span data-verbose="false">&times;</span>
    </span>
  </div>
  <input id="chat-form_js__captcha-digest" type="hidden" name="captcha-digest" disabled>
  <input id="chat-form_js__captcha-image" type="image" width="72" height="30">
  <input id="chat-form_js__captcha-answer" name="captcha-answer" placeholder="Captcha" disabled>
  <input id="chat-form_js__settings" type="image" src="/static/settings.svg" width="28" height="28" alt="Settings">
  <input id="chat-form_js__submit" type="submit" value="Chat" accesskey="p" disabled>
  <article id="chat-form_js__notice">
    <button id="chat-form_js__notice__button" type="button">
      <header id="chat-form_js__notice__button__header"></header>
      <small>Click to dismiss</small>
    </button>
  </article>
</form>
<form id="appearance-form_js" data-hidden="">
  <span id="appearance-form_js__label-name">Name:</span>
  <input id="appearance-form_js__name" name="name" maxlength="24">
  <input id="appearance-form_js__color" type="color" name="color">
  <span id="appearance-form_js__label-tripcode">Tripcode:</span>
  <input id="appearance-form_js__password" type="password" name="password" placeholder="(tripcode password)" maxlength="1024">
  <div id="appearance-form_js__row">
    <article id="appearance-form_js__row__result"></article>
    <input id="appearance-form_js__row__submit" type="submit" value="Update">
  </div>
</form>`;

const insert_jsmarkup = () => {
  if (document.getElementById("style-color") === null) {
    const style_color = document.createElement("style");
    style_color.id = "style-color";
    style_color.nonce = CSP;
    document.head.insertAdjacentElement("beforeend", style_color);
  }
  if (document.getElementById("style-tripcode-display") === null) {
    const style_tripcode_display = document.createElement("style");
    style_tripcode_display.id = "style-tripcode-display";
    style_tripcode_display.nonce = CSP;
    document.head.insertAdjacentElement("beforeend", style_tripcode_display);
  }
  if (document.getElementById("style-tripcode-colors") === null) {
    const style_tripcode_colors = document.createElement("style");
    style_tripcode_colors.id = "style-tripcode-colors";
    style_tripcode_colors.nonce = CSP;
    document.head.insertAdjacentElement("beforeend", style_tripcode_colors);
  }
  if (document.getElementById("stream_js") === null) {
    const parent = document.getElementById("stream");
    parent.insertAdjacentHTML("beforeend", jsmarkup_stream);
  }
  if (document.getElementById("info_js") === null) {
    const parent = document.getElementById("info");
    parent.insertAdjacentHTML("beforeend", jsmarkup_info);
  }
  if (document.getElementById("info_js__float") === null) {
    const parent = document.getElementById("info_js");
    parent.insertAdjacentHTML("beforeend", jsmarkup_info_float);
  }
  if (document.getElementById("info_js__float__button") === null) {
    const parent = document.getElementById("info_js__float");
    parent.insertAdjacentHTML("beforeend", jsmarkup_info_float_button);
  }
  if (document.getElementById("info_js__float__viewership") === null) {
    const parent = document.getElementById("info_js__float");
    parent.insertAdjacentHTML("beforeend", jsmarkup_info_float_viewership);
  }
  if (document.getElementById("info_js__float__uptime") === null) {
    const parent = document.getElementById("info_js__float");
    parent.insertAdjacentHTML("beforeend", jsmarkup_info_float_uptime);
  }
  if (document.getElementById("info_js__title") === null) {
    const parent = document.getElementById("info_js");
    parent.insertAdjacentHTML("beforeend", jsmarkup_info_title);
  }
  if (document.getElementById("chat-users_js") === null) {
    const parent = document.getElementById("chat__body__users");
    parent.insertAdjacentHTML("beforeend", jsmarkup_chat_users);
  }
  if (document.getElementById("chat-messages_js") === null) {
    const parent = document.getElementById("chat__body__messages");
    parent.insertAdjacentHTML("beforeend", jsmarkup_chat_messages);
  }
  if (document.getElementById("chat-form_js") === null) {
    const parent = document.getElementById("chat__form");
    parent.insertAdjacentHTML("beforeend", jsmarkup_chat_form);
  }
}

insert_jsmarkup();
const stylesheet_color = document.styleSheets[1];
const stylesheet_tripcode_display = document.styleSheets[2];
const stylesheet_tripcode_colors = document.styleSheets[3];

/* override chat form notice button */
const chat_form = document.getElementById("chat-form_js");
const chat_form_notice_button = document.getElementById("chat-form_js__notice__button");
const chat_form_notice_header = document.getElementById("chat-form_js__notice__button__header");
chat_form_notice_button.addEventListener("click", (event) => {
  chat_form.removeAttribute("data-notice");
  chat_form_notice_header.innerText = "";
});
const show_notice = (text) => {
  chat_form_notice_header.innerText = text;
  chat_form.dataset.notice = "";
}

/* override chat form settings input */
const chat_appearance_form = document.getElementById("appearance-form_js");
const chat_appearance_form_result = document.getElementById("appearance-form_js__row__result");
const chat_form_settings = document.getElementById("chat-form_js__settings");
chat_form_settings.addEventListener("click", (event) => {
  event.preventDefault();
  if (chat_appearance_form.dataset.hidden === undefined) {
    chat_appearance_form.dataset.hidden = "";
    chat_form_settings.style.backgroundColor = "";
    chat_appearance_form_result.innerText = "";
    if (!chat_appearance_form_submit.disabled) {
      chat_appearance_form.reset();
    }
  } else {
    chat_appearance_form.removeAttribute("data-hidden");
    chat_form_settings.style.backgroundColor = "#4f4f53";
  }
});

/* appearance form */
const chat_appearance_form_name = document.getElementById("appearance-form_js__name");
const chat_appearance_form_color = document.getElementById("appearance-form_js__color");
const chat_appearance_form_password = document.getElementById("appearance-form_js__password");

/* create websocket */
const info_title = document.getElementById("info_js__title");
const info_viewership = document.getElementById("info_js__float__viewership");
const info_uptime = document.getElementById("info_js__float__uptime");
const chat_messages = document.getElementById("chat-messages_js");
const chat_users_watching = document.getElementById("chat-users_js__watching");
const chat_users_watching_header = document.getElementById("chat-users_js__watching-header");
const chat_users_notwatching = document.getElementById("chat-users_js__notwatching");
const chat_users_notwatching_header = document.getElementById("chat-users_js__notwatching-header");

const create_chat_message = (object) => {
  const user = users[object.token_hash];

  const chat_message = document.createElement("li");
  chat_message.classList.add("chat-message");
  chat_message.dataset.seq = object.seq;
  chat_message.dataset.tokenHash = object.token_hash;

  const chat_message_time = document.createElement("time");
  chat_message_time.classList.add("chat-message__time");
  chat_message_time.dateTime = `${object.date}T${object.time_seconds}Z`;
  chat_message_time.title = `${object.date} ${object.time_seconds}`;
  chat_message_time.innerText = object.time_minutes;

  const chat_message_user_components = create_chat_user_components(user);

  const chat_message_markup = document.createElement("span");
  chat_message_markup.classList.add("chat-message__markup");
  chat_message_markup.innerHTML = object.markup;

  chat_message.insertAdjacentElement("beforeend", chat_message_time);
  chat_message.insertAdjacentHTML("beforeend", "&nbsp;");
  for (const chat_message_user_component of chat_message_user_components) {
    chat_message.insertAdjacentElement("beforeend", chat_message_user_component);
  }
  chat_message.insertAdjacentHTML("beforeend", ": ");
  chat_message.insertAdjacentElement("beforeend", chat_message_markup);

  return chat_message;
}
const create_chat_user_name = (user) => {
  const chat_user_name = document.createElement("span");
  chat_user_name.classList.add("chat-name");
  chat_user_name.innerText = get_user_name({user});
  //chat_user_name.dataset.color = user.color; // not working in any browser
  if (!user.broadcaster && user.name === null) {
    const b = document.createElement("b");
    b.innerText = user.tag;
    const chat_user_name_tag = document.createElement("sup");
    chat_user_name_tag.classList.add("chat-name__tag");
    chat_user_name_tag.innerHTML = b.outerHTML;
    chat_user_name.insertAdjacentElement("beforeend", chat_user_name_tag);
  }
  return chat_user_name;
}
const create_chat_user_components = (user) => {
  const chat_user_name = create_chat_user_name(user);

  const chat_user_tripcode_nbsp = document.createElement("span");
  chat_user_tripcode_nbsp.classList.add("for-tripcode");
  chat_user_tripcode_nbsp.innerHTML = "&nbsp;";

  const chat_user_tripcode = document.createElement("span");
  chat_user_tripcode.classList.add("tripcode");
  chat_user_tripcode.classList.add("for-tripcode");
  if (user.tripcode !== null) {
    chat_user_tripcode.innerHTML = user.tripcode.digest;
  }

  let result;
  if (!user.broadcaster) {
    result = [];
  } else {
    const chat_user_insignia = document.createElement("b");
    chat_user_insignia.classList.add("chat-insignia")
    chat_user_insignia.title = "Broadcaster";
    chat_user_insignia.innerText = "##";
    const chat_user_insignia_nbsp = document.createElement("span");
    chat_user_insignia_nbsp.innerHTML = "&nbsp;"
    result = [chat_user_insignia, chat_user_insignia_nbsp];
  }
  result.push(...[chat_user_name, chat_user_tripcode_nbsp, chat_user_tripcode]);
  return result;
}
const create_and_add_chat_message = (object) => {
  const chat_message = create_chat_message(object);
  chat_messages.insertAdjacentElement("beforeend", chat_message);
  while (chat_messages.children.length > max_chat_scrollback) {
    chat_messages.children[0].remove();
  }
}

let users = {};
let stats = null;
let stats_received = null;
let default_name = {true: "Broadcaster", false: "Anonymous"};
let max_chat_scrollback = 256;
const tidy_stylesheet = ({stylesheet, selector_regex, ignore_condition}) => {
  const to_delete = [];
  const to_ignore = new Set();
  for (let index = 0; index < stylesheet.cssRules.length; index++) {
    const css_rule = stylesheet.cssRules[index];
    const match = css_rule.selectorText.match(selector_regex);
    const token_hash = match === null ? null : match[1];
    const user = token_hash === null ? null : users[token_hash];
    if (user === null || user === undefined) {
      to_delete.push(index);
    } else if (!ignore_condition(token_hash, user, css_rule)) {
      to_delete.push(index);
    } else {
      to_ignore.add(token_hash);
    }
  }
  return {to_delete, to_ignore};
}
const equal = (color1, color2) => {
  /* comparing css colors is annoying */
  // when this is working, remove `ignore_other_token_hashes` from functions below
  return false;
}
const update_user_colors = (token_hash=null) => {
  ignore_other_token_hashes = token_hash !== null;
  token_hashes = token_hash === null ? Object.keys(users) : [token_hash];
  const {to_delete, to_ignore} = tidy_stylesheet({
    stylesheet: stylesheet_color,
    selector_regex: /\[data-token-hash="([a-z2-7]{26})"\] > \.chat-name/,
    ignore_condition: (this_token_hash, this_user, css_rule) => {
      const irrelevant = ignore_other_token_hashes && this_token_hash !== token_hash;
      const correct_color = equal(css_rule.style.color, this_user.color);
      return irrelevant || correct_color;
    },
  });
  // update colors
  for (const this_token_hash of token_hashes) {
    if (!to_ignore.has(this_token_hash)) {
      const user = users[this_token_hash];
      stylesheet_color.insertRule(
        `[data-token-hash="${this_token_hash}"] > .chat-name { color: ${user.color}; }`,
        stylesheet_color.cssRules.length,
      );
    }
  }
  // delete css rules
  for (const index of to_delete.reverse()) {
    stylesheet_color.deleteRule(index);
  }
}
const get_user_name = ({user=null, token_hash}) => {
  user = user || users[token_hash];
  return user.name || default_name[user.broadcaster];
}
const update_user_names = (token_hash=null) => {
  const token_hashes = token_hash === null ? Object.keys(users) : [token_hash];
  for (const chat_message of chat_messages.children) {
    const this_token_hash = chat_message.dataset.tokenHash;
    if (token_hashes.includes(this_token_hash)) {
      const user = users[this_token_hash];
      const chat_message_name = chat_message.querySelector(".chat-name");
      chat_message_name.innerHTML = create_chat_user_name(user).innerHTML;
    }
  }
}
const update_user_tripcodes = (token_hash=null) => {
  ignore_other_token_hashes = token_hash !== null;
  token_hashes = token_hash === null ? Object.keys(users) : [token_hash];
  const {to_delete: to_delete_display, to_ignore: to_ignore_display} = tidy_stylesheet({
    stylesheet: stylesheet_tripcode_display,
    selector_regex: /\[data-token-hash="([a-z2-7]{26})"\] > \.for-tripcode/,
    ignore_condition: (this_token_hash, this_user, css_rule) => {
      const irrelevant = ignore_other_token_hashes && this_token_hash !== token_hash;
      const correctly_hidden = this_user.tripcode === null && css_rule.style.display === "none";
      const correctly_showing = this_user.tripcode !== null && css_rule.style.display === "inline";
      return irrelevant || correctly_hidden || correctly_showing;
    },
  });
  const {to_delete: to_delete_colors, to_ignore: to_ignore_colors} = tidy_stylesheet({
    stylesheet: stylesheet_tripcode_colors,
    selector_regex: /\[data-token-hash="([a-z2-7]{26})"\] > \.tripcode/,
    ignore_condition: (this_token_hash, this_user, css_rule) => {
      const irrelevant = ignore_other_token_hashes && this_token_hash !== token_hash;
      const correctly_blank = (
        this_user.tripcode === null
        && css_rule.style.backgroundColor === "initial"
        && css_rule.style.color === "initial"
      );
      const correctly_colored = (
        this_user.tripcode !== null
        && equal(css_rule.style.backgroundColor, this_user.tripcode.background_color)
        && equal(css_rule.style.color, this_user.tripcode.foreground_color)
      );
      return irrelevant || correctly_blank || correctly_colored;
    },
  });

  // update colors
  for (const this_token_hash of token_hashes) {
    const tripcode = users[this_token_hash].tripcode;
    if (tripcode === null) {
      if (!to_ignore_display.has(this_token_hash)) {
        stylesheet_tripcode_display.insertRule(
          `[data-token-hash="${this_token_hash}"] > .for-tripcode { display: none; }`,
          stylesheet_tripcode_display.cssRules.length,
       );
      }
      if (!to_ignore_colors.has(this_token_hash)) {
        stylesheet_tripcode_colors.insertRule(
          `[data-token-hash="${this_token_hash}"] > .tripcode { background-color: initial; color: initial; }`,
          stylesheet_tripcode_colors.cssRules.length,
        );
      }
    } else {
      if (!to_ignore_display.has(this_token_hash)) {
        stylesheet_tripcode_display.insertRule(
          `[data-token-hash="${this_token_hash}"] > .for-tripcode { display: inline; }`,
          stylesheet_tripcode_display.cssRules.length,
        );
      }
      if (!to_ignore_colors.has(this_token_hash)) {
        stylesheet_tripcode_colors.insertRule(
          `[data-token-hash="${this_token_hash}"] > .tripcode { background-color: ${tripcode.background_color}; color: ${tripcode.foreground_color}; }`,
          stylesheet_tripcode_colors.cssRules.length,
        );
      }
    }
  }

  // delete css rules
  for (const index of to_delete_display.reverse()) {
    stylesheet_tripcode_display.deleteRule(index);
  }
  for (const index of to_delete_colors.reverse()) {
    stylesheet_tripcode_colors.deleteRule(index);
  }

  // update inner texts
  for (const chat_message of chat_messages.children) {
    const this_token_hash = chat_message.dataset.tokenHash;
    const tripcode = users[this_token_hash].tripcode;
    if (token_hashes.includes(this_token_hash)) {
      const chat_message_tripcode = chat_message.querySelector(".tripcode");
      chat_message_tripcode.innerText = tripcode === null ? "" : tripcode.digest;
    }
  }
}

const chat_form_captcha_digest = document.getElementById("chat-form_js__captcha-digest");
const chat_form_captcha_image = document.getElementById("chat-form_js__captcha-image");
const chat_form_captcha_answer = document.getElementById("chat-form_js__captcha-answer");
chat_form_captcha_image.addEventListener("loadstart", (event) => {
  chat_form_captcha_image.removeAttribute("title");
  chat_form_captcha_image.removeAttribute("data-reloadable");
  chat_form_captcha_image.alt = "Loading...";
});
chat_form_captcha_image.addEventListener("load", (event) => {
  chat_form_captcha_image.removeAttribute("alt");
  chat_form_captcha_image.dataset.reloadable = "";
  chat_form_captcha_image.title = "Click for a new captcha";
});
chat_form_captcha_image.addEventListener("error", (event) => {
  chat_form_captcha_image.alt = "Captcha failed to load";
  chat_form_captcha_image.dataset.reloadable = "";
  chat_form_captcha_image.title = "Click for a new captcha";
});
chat_form_captcha_image.addEventListener("click", (event) => {
  event.preventDefault();
  if (chat_form_captcha_image.dataset.reloadable !== undefined) {
    chat_form_submit.disabled = true;
    chat_form_captcha_image.alt = "Waiting...";
    chat_form_captcha_image.removeAttribute("title");
    chat_form_captcha_image.removeAttribute("data-reloadable");
    chat_form_captcha_image.removeAttribute("src");
    const payload = {type: "captcha"};
    ws.send(JSON.stringify(payload));
  }
});
const enable_captcha = (digest) => {
  chat_form_captcha_digest.value = digest;
  chat_form_captcha_digest.disabled = false;
  chat_form_captcha_answer.value = "";
  chat_form_captcha_answer.required = true;
  chat_form_captcha_answer.disabled = false;
  chat_form_comment.required = false;
  chat_form_captcha_image.removeAttribute("src");
  chat_form_captcha_image.src = `/captcha.jpg?token=${encodeURIComponent(TOKEN)}&digest=${encodeURIComponent(digest)}`;
  chat_form_submit.disabled = false;
  chat_form.dataset.captcha = "";
}
const disable_captcha = () => {
  chat_form.removeAttribute("data-captcha");
  chat_form_captcha_digest.disabled = true;
  chat_form_captcha_answer.disabled = true;
  chat_form_comment.required = true;
  chat_form_captcha_digest.value = "";
  chat_form_captcha_answer.value = "";
  chat_form_captcha_answer.required = false;
  chat_form_submit.disabled = false;
  chat_form_captcha_image.removeAttribute("alt");
  chat_form_captcha_image.removeAttribute("src");
}

const set_title = (title) => {
  const h1 = document.createElement("h1");
  h1.innerText = title.replaceAll(/\r?\n/g, " ");
  info_title.innerHTML = h1.outerHTML;
}

const update_uptime = () => {
  if (stats_received === null) {
    return;
  } else if (stats === null) {
    info_uptime.innerText = "";
  } else {
    const stats_received_ago = (new Date() - stats_received) / 1000;
    const uptime = Math.round(stats.uptime + stats_received_ago);

    const s = Math.round(uptime % 60);
    const m = Math.floor(uptime / 60) % 60
    const h = Math.floor(uptime / 3600);

    const ss = s.toString().padStart(2, "0");
    if (uptime < 3600) {
      info_uptime.innerText = `${m}:${ss}`;
    } else {
      const mm = m.toString().padStart(2, "0");
      info_uptime.innerText = `${h}:${mm}:${ss}`;
    }
  }
}
setInterval(update_uptime, 1000); // always update uptime

const update_viewership = () => {
  info_viewership.innerText = stats === null ? "" : `${stats.viewership} viewers`;
}

const update_stats = () => {
  if (stats === null) {
    update_viewership();
    update_uptime();
  } else {
    update_uptime();
    update_viewership();
  }
}

const update_users_list = () => {
  listed_watching = new Set();
  listed_notwatching = new Set();

  // remove no-longer-known users
  for (const element of chat_users_watching.querySelectorAll(".chat-user")) {
    const token_hash = element.dataset.tokenHash;
    if (!Object.prototype.hasOwnProperty(users, token_hash)) {
      element.remove();
    } else {
      listed_watching.add(token_hash);
    }
  }
  for (const element of chat_users_notwatching.querySelectorAll(".chat-user")) {
    const token_hash = element.dataset.tokenHash;
    if (!Object.prototype.hasOwnProperty(users, token_hash)) {
      element.remove();
    } else {
      listed_notwatching.add(token_hash);
    }
  }

  // add remaining watching/non-watching users
  const insert = (user, token_hash, is_you, chat_users_sublist) => {
    const chat_user_components = create_chat_user_components(user);
    const chat_user = document.createElement("li");
    chat_user.classList.add("chat-user");
    chat_user.dataset.tokenHash = token_hash;
    for (const chat_user_component of chat_user_components) {
      chat_user.insertAdjacentElement("beforeend", chat_user_component);
    }
    if (is_you) {
      const you = document.createElement("span");
      you.innerText = " (You)";
      chat_user.insertAdjacentElement("beforeend", you);
    }
    chat_users_sublist.insertAdjacentElement("beforeend", chat_user);
  }
  let watching = 0, notwatching = 0;
  for (const token_hash of Object.keys(users)) {
    const user = users[token_hash];
    const is_you = token_hash === TOKEN_HASH;
    if (user.watching === true && !listed_watching.has(token_hash)) {
      insert(user, token_hash, is_you, chat_users_watching);
      watching++;
    }
    if (user.watching === false && !listed_notwatching.has(token_hash)) {
      insert(user, token_hash, is_you, chat_users_notwatching);
      notwatching++;
    }
  }

  // show correct numbers
  chat_users_watching_header.innerText = `Watching (${watching})`;
  chat_users_notwatching_header.innerText = `Not watching (${notwatching})`;
}

const on_websocket_message = (event) => {
  //console.log("websocket message", event);
  const receipt = JSON.parse(event.data);
  switch (receipt.type) {
    case "error":
      console.log("ws error", receipt);
      chat_form_submit.disabled = false;
      chat_appearance_form_submit.disabled = false;
      break;

    case "init":
      console.log("ws init", receipt);

      // set title
      set_title(receipt.title);

      // update stats (uptime/viewership)
      stats = receipt.stats;
      stats_received = new Date();
      update_stats();

      // stream reload button
      if (stats === null || stream.networkState === stream.NETWORK_LOADING) {
        info_button.removeAttribute("data-visible");
      } else {
        info_button.dataset.visible = "";
      }

      // chat form nonce
      chat_form_nonce.value = receipt.nonce;

      // chat form captcha digest
      receipt.digest === null ? disable_captcha() : enable_captcha(receipt.digest);

      // chat form submit button
      chat_form_submit.disabled = false;

      // remove messages the server isn't acknowledging the existance of
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

      // settings
      default_name = receipt.default;
      max_chat_scrollback = receipt.scrollback;

      // update users
      users = receipt.users;
      update_user_names();
      update_user_colors();
      update_user_tripcodes();
      update_users_list()

      // appearance form default values
      const user = users[TOKEN_HASH];
      if (user.name !== null) {
        chat_appearance_form_name.setAttribute("value", user.name);
      }
      chat_appearance_form_name.setAttribute("placeholder", default_name[user.broadcaster]);
      chat_appearance_form_color.setAttribute("value", user.color);

      // insert new messages
      const last = chat_messages.children.length == 0 ? null : chat_messages.children[chat_messages.children.length - 1];
      const last_seq = last === null ? null : parseInt(last.dataset.seq);
      for (const message of receipt.messages) {
        if (message.seq > last_seq) {
          create_and_add_chat_message(message);
        }
      }

      break;

    case "info":
      console.log("ws info", receipt);

      // set title
      if (receipt.title !== undefined) {
        set_title(receipt.title);
      }

      // update stats (uptime/viewership)
      if (receipt.stats !== undefined) {
        stats = receipt.stats;
        stats_received = new Date();
        update_stats();
      }

      // stream reload button
      if (stats === null || stream.networkState === stream.NETWORK_LOADING) {
        info_button.removeAttribute("data-visible");
      } else {
        info_button.dataset.visible = "";
      }

      break;

    case "ack":
      console.log("ws ack", receipt);

      if (receipt.notice !== null) {
        show_notice(receipt.notice);
      }

      const existing_nonce = chat_form_nonce.value;
      if (receipt.clear && receipt.nonce === existing_nonce) {
        chat_form_comment.value = "";
      } else {
        console.log("nonce does not match ack", existing_nonce, receipt);
      }
      chat_form_nonce.value = receipt.next;
      receipt.digest === null ? disable_captcha() : enable_captcha(receipt.digest);
      chat_form_submit.disabled = false;

      break;

    case "message":
      console.log("ws message", receipt);
      create_and_add_chat_message(receipt.message);
      chat_messages.scrollTo({
        left: 0,
        top: chat_messages.scrollTopMax,
        behavior: "smooth",
      });
      break;

    case "set-users":
      console.log("ws set-users", receipt);
      for (const token_hash of Object.keys(receipt.users)) {
        users[token_hash] = receipt.users[token_hash];
      }
      update_user_names();
      update_user_colors();
      update_user_tripcodes();
      update_users_list()
      break;

    case "rem-users":
      console.log("ws rem-users", receipt);
      for (const token_hash of receipt.token_hashes) {
        delete users[token_hash];
      }
      update_user_colors();
      update_user_tripcodes();
      update_users_list()
      break;

    case "captcha":
      console.log("ws captcha", receipt);
      receipt.digest === null ? disable_captcha() : enable_captcha(receipt.digest);
      break;

    case "appearance":
      console.log("ws appearance", receipt);

      if (receipt.errors === undefined) {
        if (receipt.name !== null) {
          chat_appearance_form_name.setAttribute("value", receipt.name);
        }
        chat_appearance_form_color.setAttribute("value", receipt.color);
        chat_appearance_form_result.innerHTML = receipt.result;
      } else {
        const ul = document.createElement("ul");
        for (const error of receipt.errors) {
          const li = document.createElement("li");
          li.innerText = error[0];
          for (const tuple of error.slice(1)) {
            const mark = document.createElement("mark");
            mark.innerText = tuple[0];
            li.insertAdjacentText("beforeend", " ");
            li.insertAdjacentElement("beforeend", mark);
            li.insertAdjacentText("beforeend", tuple[1]);
          }
          ul.insertAdjacentElement("beforeend", li);
        }
        const result = document.createElement("div");
        result.innerText = "Errors:";
        result.insertAdjacentElement("beforeend", ul);
        chat_appearance_form_result.innerHTML = result.innerHTML;
      }

      chat_appearance_form_submit.disabled = false;
      chat_appearance_form.removeAttribute("data-hidden");
      chat_form_settings.style.backgroundColor = "#4f4f53";

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
  chat_live_status.innerHTML = "<span data-verbose='true'>Connecting to chat...</span><span data-verbose='false'>&middot;&middot;&middot;</span>";
  ws = new WebSocket(`ws://${document.domain}:${location.port}/live?token=${encodeURIComponent(TOKEN)}`);
  ws.addEventListener("open", (event) => {
    console.log("websocket open", event);
    chat_form_submit.disabled = false;
    chat_live_ball.style.borderColor = "green";
    chat_live_status.innerHTML = "<span><span data-verbose='true'>Connected to chat</span><span data-verbose='false'>&check;</span></span>";
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
    chat_live_status.innerHTML = "<span data-verbose='true'>Disconnected from chat</span><span data-verbose='false'>&times;</span>";
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
    chat_live_status.innerHTML = "<span>Error<span data-verbose='true'> connecting to chat</span></span>";
  });
  ws.addEventListener("message", on_websocket_message);
}

connect_websocket();

/* stream reload button */
const stream = document.getElementById("stream_js");
const info_button = document.getElementById("info_js__float__button");
info_button.addEventListener("click", (event) => {
  stream.load();
  info_button.removeAttribute("data-visible");
});
stream.addEventListener("error", (event) => {
  if (stats !== null) {
    info_button.dataset.visible = "";
  }
});

/* override js-only chat form */
const chat_form_nonce = document.getElementById("chat-form_js__nonce");
const chat_form_comment = document.getElementById("chat-form_js__comment");
const chat_form_submit = document.getElementById("chat-form_js__submit");
chat_form.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = Object.fromEntries(new FormData(chat_form));
  const payload = {type: "message", form: form};
  chat_form_submit.disabled = true;
  ws.send(JSON.stringify(payload));
});

/* override js-only appearance form */
const chat_appearance_form_submit = document.getElementById("appearance-form_js__row__submit");
chat_appearance_form.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = Object.fromEntries(new FormData(chat_appearance_form));
  const payload = {type: "appearance", form: form};
  chat_appearance_form_submit.disabled = true;
  chat_appearance_form_password.value = "";
  chat_appearance_form_result.innerText = "";
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
