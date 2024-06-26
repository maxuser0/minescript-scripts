# SPDX-FileCopyrightText: © 2024 Greg Christiana <maxuser@minescript.net>
# SPDX-License-Identifier: MIT

r"""interpreter v1 distributed via minescript.net

A Python REPL interpreter in the Minecraft chat with
Java reflection.

If a file is found in any of the directories of the config
variable `command_path` from `config.txt` with the filename
`.interpreter_init.py`, that script is loaded during startup
of the interpreter.

When the interpreter launches, the prompt ">>>" appears
in the Minecraft chat. Enter Python statements or expressions
just as you would in a Python REPL in a terminal.

Put the interpreter in the background by hitting the escape
key or deleting the ">>>" prompt to enter a Minecraft command,
chat message, or Minescript command.

Bring the interpreter to the foreground by pressing "i" while
no GUI screens are visible.

Exit the interpreter by typing "." at the ">>>" prompt.

Requires:
  minescript v4.0
  lib_java v1

Usage:
  \interpreter
"""

import faulthandler
import signal

from minescript import *
from lib_java import JavaClass, JavaObject, Float, JavaReleasePool, null
import minescript_runtime
from minescript_runtime import debug_log

import ast
import builtins
import sys
import queue
import re
import time

TAB_KEY = 258
RIGHT_KEY = 262
LEFT_KEY = 263
control_modifier = 2
enter_key = 257
trigger_key = 73 # `i` key
chat_prefix = ">>> "
last_code_time = 0

if minescript_runtime._is_debug:
  faulthandler.register(signal.SIGUSR1, minescript_runtime._debug_log)

for func in (
    log, java_access_field, java_array_index, java_array_length, java_bool, java_call_method,
    java_class, java_ctor, java_double, java_float, java_int, java_member, java_new_instance,
    java_release, java_string, java_to_string):
  func.set_default_executor(script_loop)

def is_valid_subexpression(text):
  try:
    ast.parse(text)
    return True
  except SyntaxError:
    return False


def longest_trailing_subexpression(text):
  ends_in_dot = text[-1] == "."
  if ends_in_dot:
    text = text[:-1]
  for i in range(len(text)):
    # TODO: Skip this iter of loop if prev chat and current char are both str.alnum(), i.e. only
    # split subexpression on word boundaries.
    suffix = text[i:]
    if is_valid_subexpression(suffix):
      return suffix + "." if ends_in_dot else suffix
  return None


def replace_unquoted_dot_class(text):
  """`.class` is illegal syntax in Python. So translate unquoted `.class` to `.class_`."""

  def replacer(match):
    if match.group(1):  # Inside quotes
      return match.group(0)
    else:  # Outside quotes on word boundary
      return ".class_"

  pattern = r"""
    (?P<quote>['"])  # Capture a quote
    .*?        # Match anything within quotes (non-greedy)
    (?P=quote)     # Match the same quote to close the region
    |        # OR
    \b\.class\b    # Match '.class' on word boundary
  """
  return re.sub(pattern, replacer, text, flags=re.VERBOSE)

Member_getName = None

def get_completions(target, local_vars, partial):
  global Member_getName
  if Member_getName is None:
    Member_class = java_class("java.lang.reflect.Member")
    Member_getName = java_member(Member_class, "getName")
    java_release(Member_class)

  completions = set()
  if target:
    try:
      with JavaReleasePool() as pool:
        target = builtins.eval(target)
        if isinstance(target, JavaObject):
          log(f"target -> {target} ({target.__dict__})")
          if isinstance(target, JavaClass):
            target_class = target.class_
          else:
            target_class = target.getClass()
          log(f"target class -> {target_class}")
          methods = target_class.getMethods()
          num_methods = len(methods)
          for i in range(num_methods):
            log(f"Processing method {i} of {num_methods}")
            method = pool(java_array_index(methods.id, i))
            name = java_to_string(pool(java_call_method(method, Member_getName)))
            if name.startswith(partial):
              completions.add(name + "(")
          del methods

          fields = target_class.getFields()
          num_fields = len(fields)
          for i in range(num_fields):
            log(f"Processing field {i} of {num_fields}")
            field = pool(java_array_index(fields.id, i))
            name = java_to_string(pool(java_call_method(field, Member_getName)))
            if name.startswith(partial):
              completions.add(name)
          del fields
    except Exception as e:
      echo_json({"text": f"Error: {str(e)}", "color": "red"})
  else:
    for var in local_vars:
      if var.startswith(partial):
        completions.add(var)
  return list(completions)


def longest_common_prefix(strings):
  if not strings:
    return ""
  longest = strings[0]
  for i in range(1, len(strings)):
    string = strings[i]
    end = min(len(string), len(longest))
    if end < len(longest):
      longest = longest[0:end]
    for j in range(end):
      if string[j] != longest[j]:
        longest = longest[0:j]
        break
  return longest


def process_key_event(event, local_vars):
  if event.key == trigger_key and event.action == 1 and event.screen is None:
    show_chat_screen(True, chat_prefix)
  elif abs(event.time - last_code_time) < 0.5:
    if event.key == enter_key and event.action != 1 and event.screen is None:
      show_chat_screen(True, chat_prefix)
  elif event.key == TAB_KEY and event.action == 1 and event.screen == "Chat screen":
    text, pos = chat_input()
    if text.startswith(chat_prefix) and pos == len(text):
      suffix = longest_trailing_subexpression(text[len(chat_prefix):])
      if not suffix:
        return
      last_dot = suffix.rfind(".")
      if last_dot == -1:
        target = None
        partial = suffix
      else:
        target = suffix[:last_dot]
        partial = suffix[last_dot + 1:]
      start_time = time.time()
      completions = get_completions(target, local_vars, partial)
      end_time = time.time()
      log(f"Finished completions for `{partial}` in {end_time - start_time} seconds")
      color = 0x5ee85e # green for full completion
      if len(completions) > 1:
        color = 0x5ee8e8 # cyan for partial completion
        print(" ", file=sys.stderr)
        for c in completions:
          print(c, file=sys.stderr)
      match = longest_common_prefix(completions)
      if match:
        text += match[len(partial):]
        set_chat_input(text, len(text), color)
  elif event.action == 1 and event.screen == "Chat screen" and event.key not in (
      LEFT_KEY, RIGHT_KEY) and chat_input()[0].startswith(chat_prefix):
    set_chat_input(color=0xffffff) # white for default text input


with EventQueue() as q:
  q.register_key_listener()
  q.register_outgoing_chat_interceptor(prefix=chat_prefix)
  print("Press `i` to return to the interpreter. Type `.` to exit.", file=sys.stderr)
  show_chat_screen(True, chat_prefix)

  event = None
  message = None

  # Local vars to be excluded from tab completion.
  ignore_completions = [
    "minescript_runtime", "MinescriptRuntimeOptions", "event", "message", "python_dirs", "dirname",
    "init_filename", "last_code_time", "source_code", "chat_prefix"
  ]

  Minescript = JavaClass("net.minescript.common.Minescript")

  python_dirs = os.environ["MINESCRIPT_COMMAND_PATH"].split(os.pathsep)
  for dirname in python_dirs:
    init_filename = os.path.join(dirname, ".interpreter_init.py")
    if os.path.exists(init_filename):
      with open(init_filename, "r") as init_file:
        builtins.exec(init_file.read())
      del init_file
      print("Loaded .interpreter_init.py", file=sys.stderr)
      break

  while True:
    try:
      debug_log("interpreter.py: Waiting for event queue...")
      event = q.get()
      debug_log(f"interpreter.py: Got event of type `{event.type}`")
      if event.type == EventType.OUTGOING_CHAT_INTERCEPT:
        message = event.message
        append_chat_history(message)
        if message.startswith(chat_prefix):
          last_code_time = event.time
          print(message, file=sys.stderr)
          source_code = replace_unquoted_dot_class(message[len(chat_prefix):])
          if source_code == ".":
            print("Stopping interpreter.", file=sys.stderr)
            break
          elif source_code:
            try:
              print(builtins.eval(source_code), file=sys.stderr)
              continue
            except SyntaxError:
              pass

            # Fall back to executing as statements.
            builtins.exec(source_code)
            continue

      elif event.type == EventType.KEY:
        process_key_event(event, set(locals().keys()).difference(ignore_completions))

    except Exception as e:
      echo_json({"text": f"Error: {str(e)}", "color": "red"})

    except:
      log("Unknown exception")
      echo_json({"text": "Unknown exception", "color": "red"})

  debug_log("interpreter.py:", "Exited `while` loop")

debug_log("interpreter.py:", "Exited EventQueue")
