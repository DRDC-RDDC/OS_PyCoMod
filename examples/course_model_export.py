"""Example: export a course scheduling model with processes to HTML."""

import os
import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


class Course(pcm.Model):
    """Course scheduling model with waitlist, pass and fail pools."""

    def build(self, minLoad=12, maxLoad=18, startTime=30,
              startInt=60, duration=40, passRate=0.8):
        """Define the model elements."""
        W = self.pool(0, name='W')  # waitlist
        C = self.pool(0, name='C')  # on course
        P = self.pool(0, name='P')  # pass
        F = self.pool(0, name='F')  # fail

        minLoad = self.parameter(minLoad)
        maxLoad = self.parameter(maxLoad)
        startInt = self.parameter(startInt)
        duration = self.parameter(duration)
        passRate = self.parameter(passRate)

        @self.process(start=self.wait_time(0))
        def enter():
            while True:
                W.add(8)
                yield self.wait_delay(31)

        @self.process
        def attend_serial(n):
            W.remove(n)
            C.add(n)
            yield self.wait_delay(duration)
            C.remove(n)

            np = round(n * passRate)

            P.add(np)
            F.add(n - np)

        @self.process(start=self.wait_time(startTime))
        def start():
            while True:
                if W >= minLoad:
                    n = min(int(W), maxLoad)
                    attend_serial(n).start()

                yield self.wait_delay(startInt)

        self.set_available(locals(), output=(W, C, P, F))


help_text = """
# Course Scheduling Model

This model simulates a training pipeline where students move through
a course system driven by **discrete event processes**.

## Pools

- **W (Waitlist)**: Students waiting for a course to start (starts at 0)
- **C (On Course)**: Students currently attending a course
- **P (Pass)**: Students who completed the course successfully
- **F (Fail)**: Students who did not pass

## Processes

- **enter**: Adds 8 students to the waitlist every 31 time units
  (starts at time 0)
- **attend_serial**: Removes students from the waitlist, holds them in course
  for **duration** time units, then distributes them between pass and fail
  based on **passRate**
- **start**: Checks every **startInt** time units whether the waitlist has at
  least **minLoad** students, and if so starts an **attend_serial** session
  (starts at time **startTime**)

## Build Parameters

- **minLoad** (12): Minimum students required to start a session
- **maxLoad** (18): Maximum class size per session
- **startTime** (30): Time at which the start process begins
- **startInt** (60): Interval between scheduling checks
- **duration** (40): Length of each course session (time units)
- **passRate** (0.8): Fraction of students who pass (0-1)

## How It Works

The **enter** process continuously adds students to the waitlist. The
**start** process begins at time **startTime** and checks every **startInt**
time units whether the waitlist has at least **minLoad** students. If so,
it starts an **attend_serial** session that moves up to **maxLoad** students
into the course, holds them for **duration** time units, then splits them
between pass and fail based on **passRate**.

Multiple course sessions can run concurrently - each is an independent
process on the event queue.
"""

if __name__ == "__main__":
    model = Course()
    output = pcm.export_to_html(
        model=model,
        filename="course_model.html",
        path=_HERE,
        title="Course Scheduling Model - Process Example",
        help_text=help_text,
    )
    print(f"HTML tool generated: {output}")
