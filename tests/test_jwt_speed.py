import jwt
import timeit
import sys
import math


def _format_time(timespan, precision=3):
    """Formats the timespan in a human readable form"""

    if timespan >= 60.0:
        # we have more than a minute, format that in a human readable form
        # Idea from http://snipplr.com/view/5713/
        parts = [("d", 60 * 60 * 24), ("h", 60 * 60), ("min", 60), ("s", 1)]
        time = []
        leftover = timespan
        for suffix, length in parts:
            value = int(leftover / length)
            if value > 0:
                leftover = leftover % length
                time.append("%s%s" % (str(value), suffix))
            if leftover < 1:
                break
        return " ".join(time)

    # Unfortunately characters outside of range(128) can cause problems in
    # certain terminals.
    # See bug: https://bugs.launchpad.net/ipython/+bug/348466
    # Try to prevent crashes by being more secure than it needs to
    # E.g. eclipse is able to print a µ, but has no sys.stdout.encoding set.
    units = ["s", "ms", "us", "ns"]  # the safe value
    if hasattr(sys.stdout, "encoding") and sys.stdout.encoding:
        try:
            "μ".encode(sys.stdout.encoding)
            units = ["s", "ms", "μs", "ns"]
        except Exception:
            pass
    scaling = [1, 1e3, 1e6, 1e9]

    if timespan > 0.0:
        order = min(-int(math.floor(math.log10(timespan)) // 3), 3)
    else:
        order = 3
    return "%.*g %s" % (precision, timespan * scaling[order], units[order])


class TimeitResult:
    """
    Object returned by the timeit magic with info about the run.

    Contains the following attributes:

    loops: int
      number of loops done per measurement

    repeat: int
      number of times the measurement was repeated

    best: float
      best execution time / number

    all_runs : list[float]
      execution time of each run (in s)

    compile_time: float
      time of statement compilation (s)

    """

    def __init__(self, loops, repeat, best, worst, all_runs, compile_time, precision):
        self.loops = loops
        self.repeat = repeat
        self.best = best
        self.worst = worst
        self.all_runs = all_runs
        self.compile_time = compile_time
        self._precision = precision
        self.timings = [dt / self.loops for dt in all_runs]

    @property
    def average(self):
        return math.fsum(self.timings) / len(self.timings)

    @property
    def stdev(self):
        mean = self.average
        return (math.fsum([(x - mean) ** 2 for x in self.timings]) / len(self.timings)) ** 0.5

    def __str__(self):
        pm = "+-"
        if hasattr(sys.stdout, "encoding") and sys.stdout.encoding:
            try:
                "\xb1".encode(sys.stdout.encoding)
                pm = "\xb1"
            except Exception:
                pass
        return "{mean} {pm} {std} per loop (mean {pm} std. dev. of {runs} run{run_plural}, {loops:,} loop{loop_plural} each)".format(
            pm=pm,
            runs=self.repeat,
            loops=self.loops,
            loop_plural="" if self.loops == 1 else "s",
            run_plural="" if self.repeat == 1 else "s",
            mean=_format_time(self.average, self._precision),
            std=_format_time(self.stdev, self._precision),
        )

    def _repr_pretty_(self, p, cycle):
        unic = self.__str__()
        p.text("<TimeitResult : " + unic + ">")


def run_timeit(stmt="pass", setup="pass", timer=timeit.default_timer, repeat=5, number=1000000, globals=None):
    tc_min = 0.1
    tc = tc_min
    precision = 3

    all_runs = timeit.repeat(stmt=stmt, setup=setup, timer=timer, repeat=repeat, number=number, globals=globals)
    best = min(all_runs) / number
    worst = max(all_runs) / number
    timeit_result = TimeitResult(number, repeat, best, worst, all_runs, tc, precision)
    return timeit_result


key = "51127d349d31c47857749d23ec9633d7b359a18a83e07a3051d937fbadac32695b2cd2c75b5260b4a4de6aa7d18ae772b06688c9b076414d7e1ea36adc348162"


def encode():
    """Stupid test function"""
    _ = jwt.encode({"user": "user1", "something_else": "some_string"}, key, algorithm="HS256")


def decode():
    """Stupid test function"""
    encoded = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzb21lIjoicGF5bG9hZCJ9.ZYAdMXCEDiKgRh7RsUk-Qi9AtIQHDrn2t7qkN7ge1sE"
    jwt.decode(encoded, key, algorithms="HS256")


def test_jwt_decode_speed():
    print("decode jwt")
    a = run_timeit(decode, number=1000)
    print(a)
    assert a.worst < 10e-5


def test_jwt_encode_speed():
    print("encode jwt")
    a = run_timeit(encode, number=1000)
    print(a)
    assert a.worst < 10e-5


if __name__ == "__main__":
    print("encode jwt")
    a = run_timeit("encode()", setup="from __main__ import encode", number=1000)
    print(a)
    print("decode jwt")
    a = run_timeit("decode()", setup="from __main__ import decode", number=1000)
    print(a)
