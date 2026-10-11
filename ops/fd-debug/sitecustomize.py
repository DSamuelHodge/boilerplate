"""Temporary fd-leak diagnostic, active only when FD_DEBUG=1.

Wraps the asyncio default event-loop policy to log a stack trace each time
an event loop is created. Used to identify the source of unclosed event
loops exhausting the container's file-descriptor limit.

Deployed via a read-only volume mount; remove the mount + this file once
the leak is fixed. Everything is defensive: any failure here must never
break interpreter startup.
"""

import asyncio
import os
import traceback

try:
    if os.getenv("FD_DEBUG") == "1":
        _policy_cls = asyncio.DefaultEventLoopPolicy
        _orig_new_loop = _policy_cls.new_event_loop
        _state = {"count": 0}

        def _traced_new_event_loop(self):
            loop = _orig_new_loop(self)
            _state["count"] += 1
            n = _state["count"]
            try:
                # Log the first few creations in full, then sample.
                if n <= 15 or n % 100 == 0:
                    with open(
                        "/tmp/loop_creation.log", "a"
                    ) as f:
                        f.write(f"=== loop #{n} ===\n")
                        traceback.print_stack(file=f)
                        f.write("\n")
            except Exception:
                pass
            return loop

        _policy_cls.new_event_loop = _traced_new_event_loop
except Exception:
    pass
