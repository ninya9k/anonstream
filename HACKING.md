## Hacking

By default anonstream has two APIs it exposes through two UNIX sockets:
the control socket `control.sock` and the event socket `event.sock`.  If
the platform you are using does not support UNIX sockets, they can be
disabled in the config.

### Control socket

The control socket allows reading and modifying internal state, e.g.
setting the title or changing a user's name.  Currently the control
socket has checks to see if what you're doing is sane, but they're not
comprehensive; you could craft commands that lead to undefined
behaviour.  If you have `socat`, you can use the control socket
interactively like this:
```sh
rlwrap socat STDIN UNIX-CONNECT:control.sock
```
`rlwrap` only adds line editing and is optional. If you don't have it
you can still get (inferior) line editing by doing:
```sh
socat READLINE UNIX-CONNECT:control.sock
```
Once connected, type "help" and press enter to get a list of commands.

### Event socket

The event socket is a read-only socket that sends out internal events as
they happen.  Currently the only supported event is a chat message being
added.  The intended use is to hook into other applications that depend
on chat, e.g.  text-to-speech or Twitch Plays Pokémon.

View events like this:
```sh
socat UNIX-CONNECT:event.sock STDOUT
```

Sidenote, this will still read from stdin, and if you send anything on
stdin the event socket will close itself.  If you want to ignore stdin,
I couldn't figure out how to get `socat` to do it so you can do it like
this:
```sh
cat > /dev/null | socat UNIX-CONNECT:event.sock STDOUT
```
If you do this `cat` will not exit when the connection is closed so you
will probably have to interrupt it with `^C`.

#### Examples

If you have `jq` you can view prettified events like this:
```sh
socat UNIX-CONNECT:event.sock STDOUT | jq
```
(On older versions of `jq` you have to say `jq .` when reading from
stdin.)

Use this to get each new chat message on a new line:
```sh
socat UNIX-CONNECT:event.sock STDOUT | jq 'select(.type == "message") | .event.nomarkup'
```

##### Text-to-speech

This command will take each new chat message with the prefix "!say ",
strip the prefix, and synthesize the rest of the message as speech using
`espeak`:
```sh
socat UNIX-CONNECT:event.sock STDOUT \
| jq --unbuffered 'select(.type == "message") | .event.nomarkup' \
| grep -E --line-buffered '^"!say ' \
| sed -Eu 's/^"!say /"/' \
| jq -r --unbuffered \
| espeak
```
