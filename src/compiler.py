import re, os

class PDDLCompiler:
    RESULT_PREDS = {
        "pick-up":   lambda a: [("holding", [a[0]])],
        "put-down":  lambda a: [("ontable", [a[0]]), ("clear", [a[0]])],
        "stack":     lambda a: [("on",      [a[0], a[1]])],
        "unstack":   lambda a: [("holding", [a[0]]), ("clear", [a[1]])],
        "drive-truck":     lambda a: [("at-vehicle", [a[0], a[2]])],
        "fly-airplane":    lambda a: [("at-vehicle", [a[0], a[2]])],
        "load-truck":      lambda a: [("in-vehicle", [a[0], a[1]])],
        "unload-truck":    lambda a: [("at-package", [a[0], a[2]])],
        "load-airplane":   lambda a: [("in-vehicle", [a[0], a[1]])],
        "unload-airplane": lambda a: [("at-package", [a[0], a[2]])],
        "move":            lambda a: [("at", [a[1]])],
        "move-with-key":   lambda a: [("at", [a[1]])],
        "pick-up-key":     lambda a: [("carrying", [a[0]])],
        "put-down-key":    lambda a: [("at-key", [a[0], a[1]])],
        "do-port-scan":        lambda a: [("port-scanned",       a)],
        "do-find-vuln":        lambda a: [("vuln-found",         a)],
        "do-run-exploit":      lambda a: [("exploit-run",        a)],
        "do-get-shell":        lambda a: [("got-shell",          a)],
        "do-escalate-privs":   lambda a: [("priv-escalated",     a)],
        "do-install-backdoor": lambda a: [("backdoor-installed", a)],
        "do-list-files":       lambda a: [("files-listed",       a)],
        "do-download-data":    lambda a: [("data-downloaded",    a)],
        "do-deface":           lambda a: [("defaced",            a)],
    }

    def __init__(self, domain_file, problem_file, observations):
        if not observations:
            raise ValueError("Empty observations")
        self.domain_file  = domain_file
        self.problem_file = problem_file
        self.observations = [o.strip().lower() for o in observations]
        self._domain_text  = open(domain_file,  encoding="utf-8", errors="replace").read()
        self._problem_text = open(problem_file, encoding="utf-8", errors="replace").read()
        self._obs_unique   = self._uniquify(self.observations)

    def _action_name(self, o): return o.split()[0]
    def _action_args(self, o): return o.split()[1:]

    def _fluent(self, s):
        c = re.sub(r'[\s\-]+', '_', s)
        c = re.sub(r'[^a-z0-9_]', '', c)
        return 'obs__' + c

    def _uniquify(self, obs):
        seen = {}; r = []
        for o in obs:
            if o not in seen: seen[o] = 0; r.append(o)
            else: seen[o] += 1; r.append(o + '_dup' + str(seen[o]))
        return r

    def _block(self, text, start):
        d = 0
        for i in range(start, len(text)):
            if   text[i] == '(': d += 1
            elif text[i] == ')':
                d -= 1
                if d == 0: return text[start:i+1], i+1
        raise ValueError('Unmatched paren at %d' % start)

    def _inject_req(self, text, req):
        m = re.compile(r'\(:requirements\b', re.I).search(text)
        if m:
            blk, end = self._block(text, m.start())
            if req not in blk.lower():
                text = text[:m.start()] + blk[:-1] + ' ' + req + ')' + text[end:]
        return text

    def _parse_typed_list(self, content):
        result = {}
        for seg in re.finditer(r'([^-]+)-\s*(\S+)', content):
            for o in seg.group(1).split():
                result[o] = seg.group(2)
        return result

    def _get_all_obs_objects(self):
        m = re.compile(r'\(:objects(.*?)\)', re.I | re.DOTALL).search(self._problem_text)
        obj_types = self._parse_typed_list(m.group(1)) if m else {}
        result = {}
        for obs in self.observations:
            for o in self._action_args(obs):
                if o not in result:
                    result[o] = obj_types.get(o)
        return result

    def _remove_obs_objects(self, problem_text, to_remove):
        m = re.compile(r'\(:objects(.*?)\)', re.I | re.DOTALL).search(problem_text)
        if not m:
            return problem_text
        content = m.group(1)
        groups = []
        for seg in re.finditer(r'([^-]+)-\s*(\S+)', content):
            objs = [o for o in seg.group(1).split() if o not in to_remove]
            typ  = seg.group(2)
            if objs:
                groups.append((typ, objs))
        inner = '  '.join(' '.join(objs) + ' - ' + typ for typ, objs in groups)
        new_objects = '(:objects ' + inner + ')'
        return problem_text[:m.start()] + new_objects + problem_text[m.end():]

    def _build_domain(self):
        text = self._domain_text
        text = self._inject_req(text, ':adl')

        preds = '\n'.join('        (' + self._fluent(u) + ')' for u in self._obs_unique)
        m = re.compile(r'\(:predicates\b', re.I).search(text)
        if not m: raise ValueError('No (:predicates) in domain')
        _, end = self._block(text, m.start())
        text = text[:end-1] + '\n' + preds + '\n    ' + text[end-1:]

        obs_objs = self._get_all_obs_objects()
        if obs_objs:
            by_type = {}
            for obj, typ in obs_objs.items():
                by_type.setdefault(typ or 'object', []).append(obj)
            lines = ['  (:constants']
            for typ, objs in sorted(by_type.items()):
                lines.append('    ' + ' '.join(sorted(set(objs))) + ' - ' + typ)
            lines.append('  )')
            const_block = '\n'.join(lines) + '\n'
            pred_idx = re.compile(r'\(:predicates\b', re.I).search(text).start()
            text = text[:pred_idx] + const_block + text[pred_idx:]

        for i, (orig, uniq) in enumerate(zip(self.observations, self._obs_unique)):
            act_name = self._action_name(orig)
            act_args = self._action_args(orig)
            prev_fl  = self._fluent(self._obs_unique[i-1]) if i > 0 else None
            cur_fl   = self._fluent(uniq)

            result_fn = self.RESULT_PREDS.get(act_name)
            prec_atoms = []
            if result_fn and act_args:
                for pred, args in result_fn(act_args):
                    prec_atoms.append('(' + pred + ' ' + ' '.join(args) + ')')
            if prev_fl:
                prec_atoms.append('(' + prev_fl + ')')

            if   len(prec_atoms) == 0: prec = '(and)'
            elif len(prec_atoms) == 1: prec = prec_atoms[0]
            else:                      prec = '(and ' + ' '.join(prec_atoms) + ')'

            step = (
                '\n  (:action obs-step-%d\n'
                '    :parameters ()\n'
                '    :precondition %s\n'
                '    :effect (%s)\n'
                '  )' % (i, prec, cur_fl)
            )
            last = text.rfind(')')
            text = text[:last] + step + '\n' + text[last:]

        return text

    def _build_problem(self, goal_atoms, compliant):
        last_fl  = self._fluent(self._obs_unique[-1])
        obs_goal = ('(' + last_fl + ')' if compliant else '(not (' + last_fl + '))')
        text     = self._problem_text

        obs_objs = set(self._get_all_obs_objects().keys())
        if obs_objs:
            text = self._remove_obs_objects(text, obs_objs)

        # Find and REPLACE the entire (:goal ...) block with goal_atoms + obs_goal
        m = re.compile(r'\(:goal\b', re.I).search(text)
        if not m: raise ValueError('No (:goal in problem')
        goal_block, goal_end = self._block(text, m.start())
        new_goal = ('(:goal\n    (and\n      '
                    + '\n      '.join(goal_atoms)
                    + '\n      ' + obs_goal
                    + '\n    )\n  )')
        return text[:m.start()] + new_goal + text[goal_end:]

    def compile(self, out_dir, goal_atoms):
        os.makedirs(out_dir, exist_ok=True)
        dom   = self._build_domain()
        comp  = self._build_problem(goal_atoms, True)
        ncomp = self._build_problem(goal_atoms, False)
        dp = os.path.join(out_dir, 'domain_obs.pddl')
        cp = os.path.join(out_dir, 'problem_compliant.pddl')
        np = os.path.join(out_dir, 'problem_noncompliant.pddl')
        open(dp, 'w').write(dom)
        open(cp, 'w').write(comp)
        open(np, 'w').write(ncomp)
        return {'domain': dp, 'compliant': cp, 'noncompliant': np}


def compile_pr_problem(d, p, obs, goal, out):
    return PDDLCompiler(d, p, obs).compile(out, goal)
