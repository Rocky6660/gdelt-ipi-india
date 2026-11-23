import sys
p=sys.argv[1]; s=open(p).read()
old='''    for m in months:
        out.append({"group": m,
                    "window": [d for d in parts["window"] if d.strftime("%Y-%m") == m],
                    "other": [d for d in parts["other"] if d.strftime("%Y-%m") == m]})
    return out'''
new='''    for m in months:
        w = [d for d in parts["window"] if d.strftime("%Y-%m") == m]
        o = [d for d in parts["other"] if d.strftime("%Y-%m") == m]
        # D4.4(i) one-scan: BigQuery bills the union of both references' columns over all listed partitions,
        # so window days (full set) and other days (reduced set) go in SEPARATE jobs of the same template.
        if w:
            out.append({"group": m, "window": w, "other": []})
        if o:
            out.append({"group": m, "window": [], "other": o})
    return out


def q2_split_dry(c, cfg, ledger, label, sql_file, window, other, sources, inline=None) -> int:
    """Q2 bytes as actually run: window-only job + other-only job (each exactly one scan of its columns)."""
    b = 0
    if window:
        b += do_dry_run(c, cfg, ledger, f"{label}_w", sql_file, build_q2_params(window, [], sources, cfg), inline=inline)
    if other:
        b += do_dry_run(c, cfg, ledger, f"{label}_o", sql_file, build_q2_params([], other, sources, cfg), inline=inline)
    return b'''
assert old in s; s=s.replace(old,new)
old='''        params = build_q2_params(parts["window"], parts["other"], srcs, cfg)
        b = do_dry_run(c, cfg, ledger, f"ladder_{rung}", f"{cfg['paths']['sql_dir']}/q2_stage_template.sql", params,
                       inline=a.inline_partitions or None)'''
new='''        b = q2_split_dry(c, cfg, ledger, f"ladder_{rung}", f"{cfg['paths']['sql_dir']}/q2_stage_template.sql",
                         parts["window"], parts["other"], srcs, inline=a.inline_partitions or None)'''
assert old in s; s=s.replace(old,new)
old='''    q2 = do_dry_run(c, cfg, ledger, f"ladder_{a.rung}", f"{cfg['paths']['sql_dir']}/q2_stage_template.sql",
                    build_q2_params(parts["window"], parts["other"], read_top20_domains(cfg), cfg),
                    inline=a.inline_partitions or None)'''
new='''    q2 = q2_split_dry(c, cfg, ledger, f"ladder_{a.rung}", f"{cfg['paths']['sql_dir']}/q2_stage_template.sql",
                      parts["window"], parts["other"], read_top20_domains(cfg), inline=a.inline_partitions or None)'''
assert old in s; s=s.replace(old,new)
with open(p,'r+') as f: f.seek(0); f.write(s); f.truncate()
print("patched",p)
