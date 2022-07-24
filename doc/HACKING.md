## Hacking

By default anonstream has two private APIs it exposes through two UNIX
sockets: the control socket `control.sock` and the event socket
`event.sock`.  If the platform you are on does not support UNIX sockets,
they can be disabled in the config.

### Control socket

The control socket allows reading and modifying internal state, e.g.
setting the title or changing a user's name.  Currently the control
socket has checks to see if what you're doing is sane, but they're non-
comprehensive; you could craft commands that lead to undefined
behaviour.  If you have `socat`, you can use the control socket
interactively like this:
```sh
socat READLINE UNIX-CONNECT:control.sock
```
If you have it, you can use `rlwrap` to get line editing that's a bit
nicer:
```sh
rlwrap socat STDIN UNIX-CONNECT:control.sock
```
Once connected, type "help" and press enter to get a list of commands.

### Event socket

The event socket is a read-only socket that sends out internal events as
they happen.  Currently the only supported event is a chat message being
added.  The intended use is to hook into other applications that depend
on chat, e.g. text-to-speech or Twitch Plays Pokémon.

View events like this:
```sh
socat -u UNIX-CONNECT:event.sock STDOUT
```

#### Examples

If you have `jq` you can view prettified events like this:
```sh
socat -u UNIX-CONNECT:event.sock STDOUT | jq
```
(On older versions of `jq` you have to say `jq .` when reading from
stdin.)

Use this to get each new chat message on a new line:
```sh
socat -u UNIX-CONNECT:event.sock STDOUT | jq 'select(.type == "message") | .event.nomarkup'
```

##### Text-to-speech

This command will take each new chat message with the prefix "!say ",
strip the prefix, and synthesize the rest of the message as speech using
`espeak`:
```sh
socat -u UNIX-CONNECT:event.sock STDOUT \
| jq --unbuffered 'select(.type == "message") | .event.nomarkup' \
| grep -E --line-buffered '^"!say ' \
| sed -Eu 's/^"!say /"/' \
| jq -r --unbuffered \
| espeak
```
