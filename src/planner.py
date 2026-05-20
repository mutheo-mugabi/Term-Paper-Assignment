import subprocess, os, re, time, tempfile, shutil

INFINITY = 1e7

class PlannerResult:
    def __init__(self):
        self.cost = INFINITY
        self.wall_time = 0.0
        self.success = False
        self.timeout = False
        self.plan = []

class FastDownward:
    """
    Fast Downward wrapper.
    IMPORTANT: astar(lmcut()) does NOT support conditional effects.
    We use:
      optimal -> astar(blind())   supports conditional effects, admissible
      greedy  -> lazy_greedy([add()]) supports conditional effects
    """
    def __init__(self, fd_path="fast-downward.py",
                 mode="optimal", time_limit=300.0, memory_mb=4096):
        self.fd_path    = str(fd_path)
        self.mode       = mode
        self.time_limit = time_limit
        if mode not in ("optimal","greedy","anytime"):
            raise ValueError(f"Unknown mode {mode}")

    def solve(self, domain_file, problem_file):
        result = PlannerResult()
        fd  = os.path.abspath(self.fd_path)
        dom = os.path.abspath(domain_file)
        prb = os.path.abspath(problem_file)

        # Use configurations that support conditional effects
        if self.mode == "optimal":
            search = "astar(blind())"
        elif self.mode == "greedy":
            search = "lazy_greedy([add()], preferred=[add()])"
        else:
            search = "lazy_wastar([add()],w=5)"

        tmpdir = tempfile.mkdtemp()
        try:
            plan_path  = os.path.join(tmpdir, "found_plan")
            stdout_log = os.path.join(tmpdir, "stdout.txt")
            stderr_log = os.path.join(tmpdir, "stderr.txt")

            cmd = ["python3", fd,
                   "--search-time-limit", str(int(self.time_limit)),
                   "--plan-file", plan_path,
                   dom, prb,
                   "--search", search]

            start = time.time()
            try:
                with open(stdout_log,"w") as fo, open(stderr_log,"w") as fe:
                    proc = subprocess.run(cmd, stdout=fo, stderr=fe,
                                          timeout=self.time_limit+60,
                                          cwd=tmpdir)
                result.wall_time = time.time()-start

                out = open(stdout_log, encoding="utf-8",
                            errors="replace").read()

                if proc.returncode == 23:
                    result.timeout = True
                    return result

                if os.path.exists(plan_path):
                    self._parse(plan_path, result)
                if not result.success:
                    alt = plan_path+".1"
                    if os.path.exists(alt):
                        self._parse(alt, result)

            except subprocess.TimeoutExpired:
                result.wall_time = time.time()-start
                result.timeout = True
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        return result

    def _parse(self, path, result):
        txt = open(path, encoding="utf-8", errors="replace").read()
        m = re.search(r";\s*cost\s*=\s*([0-9]+)", txt)
        if m:
            result.cost = float(m.group(1))
        actions = []
        for line in txt.splitlines():
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith("(") and line.endswith(")"):
                line = line[1:-1].strip()
            line = re.sub(r"\s*\(\d+\)\s*$","",line).strip()
            if line:
                actions.append(line)
        if actions:
            result.plan = actions
            result.success = True
            if result.cost == INFINITY:
                result.cost = float(len(actions))

def run_planner(domain, problem, fd_path="fast-downward.py",
                mode="optimal", time_limit=300.0):
    return FastDownward(fd_path=fd_path, mode=mode,
                        time_limit=time_limit).solve(domain, problem)