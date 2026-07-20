"""Example: export a course scheduling model with processes to HTML."""

import os
import pycomod as pcm

_HERE = os.path.dirname(os.path.abspath(__file__))


class CourseModel(pcm.Model):
    def build(self):
        # Pools
        W = self.pool(100)     # Waitlist
        C = self.pool(0)       # In course
        P = self.pool(0)       # Passed
        F = self.pool(0)       # Failed

        # Parameters
        duration = self.parameter(5)
        passRate = self.parameter(0.8)
        maxLoad = self.parameter(30)
        minLoad = self.parameter(10)
        startInt = self.parameter(10)

        # Process: run a single course session
        @self.process
        def attend(n):
            W.remove(n)
            C.add(n)
            yield self.wait_delay(duration)
            C.remove(n)
            np_val = round(n * passRate)
            P.add(np_val)
            F.add(n - np_val)

        # Process: schedule courses periodically
        @self.process(start=self.wait_time(2))
        def scheduler():
            while True:
                if W >= minLoad:
                    n = min(int(W), maxLoad)
                    attend(n).start()
                yield self.wait_delay(startInt)

        self.set_available(locals(), output=(W, C, P, F))


help_text = """
# Course Scheduling Model

This model simulates a training pipeline where students move through
a course system driven by **discrete event processes**.

## Pools

- **W (Waitlist)**: Students waiting for a course to start
- **C (In Course)**: Students currently attending a course
- **P (Passed)**: Students who completed the course successfully
- **F (Failed)**: Students who did not pass

## Parameters

- **duration**: Length of each course session (time units)
- **passRate**: Fraction of students who pass (0–1)
- **maxLoad**: Maximum class size per session
- **minLoad**: Minimum students required to start a session
- **startInt**: Interval between scheduling checks

## How It Works

The **scheduler** process starts at time 2 and checks every **startInt**
time units whether the waitlist has at least **minLoad** students. If so,
it starts an **attend** session that removes students from the waitlist,
holds them in course for **duration** time units, then distributes them
between passed and failed based on **passRate**.

Multiple course sessions can run concurrently — each is an independent
process on the event queue.
"""

if __name__ == "__main__":
    model = CourseModel()
    output = pcm.export_to_html(
        model=model,
        filename="course_model.html",
        path=_HERE,
        title="Course Scheduling Model - Process Example",
        help_text=help_text,
    )
    print(f"HTML tool generated: {output}")
