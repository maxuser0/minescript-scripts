# SPDX-FileCopyrightText: © 2022 Greg Christiana <maxuser@minescript.net>
# SPDX-License-Identifier: MIT

r"""eval v1 distributed via minescript.net

Usage:
  \eval <pythonCode>

Executes <pythonCode> as either a Python expression (code
that can appear on the right-hand side of an assignment, in
which case the value is echoed to the chat screen) or Python
statements (e.g. a `for` loop).

Functions from minescript.py are available automatically without
qualification.

Multiple lines of code can be written using escaped newlines
(`\n`).

Examples:
  Print information about nearby entities to the chat screen:
  \eval "entities()"
  (note: entities() added in Minescript v2.1)

  Print the names of nearby entities to the chat screen:
  \eval "for e in entities(): echo(e['name'])"
  (note: entities() added in Minescript v2.1)

  Import `time` module, sleep 3 seconds, and take a screenshot:
  \eval "import time\ntime.sleep(3)\nscreenshot()"
  (note: screenshot() added in Minescript v2.1)

"""

# `from ... import *` is normally considered poor form because of namespace
# pollution.  But it's desirable in this case because it allows single-line
# Python code that's entered in the Minecraft chat screen to omit the module
# prefix for brevity. And brevity is important for this use case.
from minescript import *
from typing import Any
import builtins
import sys

def run(python_code: str) -> None:
  """Executes python_code as an expression or statements.

  Args:
    python_code: Python expression or statements (newline-delimited)
  """
  # Try to evaluate as an expression.
  try:
    print(builtins.eval(python_code), file=sys.stderr)
    return
  except SyntaxError:
    pass

  # Fall back to executing as statements.
  builtins.exec(python_code)


if __name__ == "__main__":
  if len(sys.argv) != 2:
    print(
        f"eval.py: Expected 1 parameter, instead got {len(sys.argv) - 1}: {sys.argv[1:]}",
        file=sys.stderr)
    print(r"Usage: \eval <pythonCode>", file=sys.stderr)
    sys.exit(1)

  run(sys.argv[1])
