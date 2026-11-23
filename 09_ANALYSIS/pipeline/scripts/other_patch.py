import sys
p=sys.argv[1]; s=open(p).read()
def rep(o,n,cnt=1):
    global s
    assert s.count(o)>=1, o[:60]; s=s.replace(o,n) if cnt==0 else s.replace(o,n,cnt)
rep('STAGE_Q2_SQL_PREFIX = "q2_stage_template"','STAGE_Q2_SQL_PREFIX = "q2_stage_"')
rep('''    if other:
        b += do_dry_run(c, cfg, ledger, f"{label}_o", sql_file, build_q2_params([], other, sources, cfg), inline=inline)''',
'''    if other:
        b += do_dry_run(c, cfg, ledger, f"{label}_o", q2_sql_for(cfg, [], other),
                        build_q2_params([], other, sources, cfg), inline=inline)''')
rep('''def q2_split_dry(''','''def q2_sql_for(cfg, window, other) -> str:
    """Window-day jobs: q2_stage_template.sql (other_ts empty). Other-day jobs: q2_stage_other.sql (one scan)."""
    if window and other:
        raise ValueError("a Q2 job may not mix window and other days (one-scan rule)")
    return f"{cfg['paths']['sql_dir']}/" + ("q2_stage_template.sql" if window else "q2_stage_other.sql")


def q2_split_dry(''')
rep('''    sql_file = f"{cfg['paths']['sql_dir']}/q2_stage_template.sql"
    chunks = []''','''    chunks = []''')
rep('''            return do_dry_run(c, cfg, ledger, "q2_plan", sql_file,''','''            return do_dry_run(c, cfg, ledger, "q2_plan", q2_sql_for(cfg, x["window"], x["other"]),''')
rep('''        do_dry_run(c, cfg, ledger, ch["label"], sql_file, build_q2_params(ch["window"], ch["other"], sources, cfg),''',
'''        do_dry_run(c, cfg, ledger, ch["label"], q2_sql_for(cfg, ch["window"], ch["other"]),
                   build_q2_params(ch["window"], ch["other"], sources, cfg),''')
rep('''        do_run(c, cfg, Ledger(rpath(cfg, "ledger")), ch["label"], f"{cfg['paths']['sql_dir']}/q2_stage_template.sql",''',
'''        do_run(c, cfg, Ledger(rpath(cfg, "ledger")), ch["label"], q2_sql_for(cfg, [D(d) for d in ch["window"]], [D(d) for d in ch["other"]]),''')
with open(p,'r+') as f: f.seek(0); f.write(s); f.truncate()
print("patched",p)
