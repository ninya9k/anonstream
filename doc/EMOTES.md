## Emotes

Emotes are small images that are inserted into chat messages in place of
given strings.  To add emotes, add entries to `emotes.json` that look
like below, then restart the server.

```json
{
  "name": ":joy:",
  "file": "joy.png",
  "width": 20,
  "height": 24
}
```
```json
{
  "name": "JoySpin",
  "file": "emote/joyspin.gif",
  "width": null,
  "height": 24
}
```

* `name` is the string that will be replaced in chat messages.

* `file` is the location of the emote image relative to the static
  directory `anonstream/static`.  The file must actually be in the
  static directory or a subdirectory of it.

* `width` and `height` are the dimensions the inserted <img> element
  will have.  Each can be either a non-negative integer or `null`
  (automatic width/height).
