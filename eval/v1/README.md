## `eval v1`

Executes the given parameter as Python code.

&nbsp;

**Usage**

```
\eval <pythonCode>
```

Executes `<pythonCode>` as either a Python expression (code
that can appear on the right-hand side of an assignment, in
which case the value is echoed to the chat screen) or Python
statements (e.g. a `for` loop).

Functions from minescript.py are available automatically without
qualification.

Multiple lines of code can be written using escaped newlines
(`\n`).

&nbsp;

**Examples**

Print information about nearby entities to the chat screen:

```
\eval "entities()"
```
*(note: entities() added in Minescript v2.1)*

Print the names of nearby entities to the chat screen:

```
\eval "for e in entities(): echo(e['name'])"
```
*(note: entities() added in Minescript v2.1)*

Import `time` module, sleep 3 seconds, and take a screenshot:

```
\eval "import time\ntime.sleep(3)\nscreenshot()"
```
*(note: screenshot() added in Minescript v2.1)*
